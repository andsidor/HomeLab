#!/usr/bin/env python3
"""Pobieranie danych przez Garmin Connect Personal API."""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from garmin_personal_api import GarminPersonalApiClient, PersonalApiAuthenticator
from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway


def create_api_client(token_cache_path: Path) -> GarminPersonalApiClient:
    api_key = os.environ.get("GARMIN_PERSONAL_API_KEY")
    if not api_key:
        raise RuntimeError("Brak klucza GARMIN_PERSONAL_API_KEY.")

    with PersonalApiAuthenticator(bearer_token_cache_file=token_cache_path) as authenticator:
        token = authenticator.obtain_token(api_key)
    return GarminPersonalApiClient(token.access_token)


def save(data, name: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Zapisano: {path}")


def metric_number(data: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        for value in data.values():
            result = metric_number(value, keys)
            if result is not None:
                return result
    elif isinstance(data, list):
        for value in data:
            result = metric_number(value, keys)
            if result is not None:
                return result
    return None


def activity_total(activities, key):
    return sum(
        activity[key]
        for activity in activities
        if isinstance(activity, dict)
        and isinstance(activity.get(key), (int, float))
        and not isinstance(activity.get(key), bool)
    )


def init_database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_data (
            day TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activities (
            activity_id TEXT PRIMARY KEY,
            activity_date TEXT,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    return connection


def collect_stored_metrics(connection: sqlite3.Connection) -> dict[str, int | float]:
    metrics: dict[str, int | float] = {
        "garmin_steps_total": 0,
        "garmin_distance_meters_total": 0,
        "garmin_active_calories_total": 0,
        "garmin_sleep_duration_seconds_total": 0,
        "garmin_resting_heart_rate_bpm": 0,
        "garmin_sync_days_stored": 0,
        "garmin_sync_activities_stored": 0,
        "garmin_activity_distance_meters_total": 0,
        "garmin_activity_duration_seconds_total": 0,
        "garmin_activity_calories_total": 0,
    }
    daily_metric_keys: dict[str, tuple[str, tuple[str, ...]]] = {
        "garmin_steps_total": ("stats", ("totalSteps", "steps")),
        "garmin_distance_meters_total": (
            "stats",
            ("totalDistanceMeters", "distanceInMeters"),
        ),
        "garmin_active_calories_total": ("stats", ("activeKilocalories", "activeCalories")),
        "garmin_sleep_duration_seconds_total": ("sleep", ("sleepTimeSeconds",)),
        "garmin_resting_heart_rate_bpm": ("heart_rate", ("restingHeartRate",)),
    }
    daily_values = {name: [] for name in daily_metric_keys}
    daily_rows = connection.execute("SELECT payload FROM daily_data")
    for (payload,) in daily_rows:
        day_data = json.loads(payload)
        for metric_name, (section, keys) in daily_metric_keys.items():
            value = metric_number(day_data.get(section), keys)
            if value is not None:
                daily_values[metric_name].append(value)

    metrics["garmin_sync_days_stored"] = connection.execute(
        "SELECT COUNT(*) FROM daily_data"
    ).fetchone()[0]
    for metric_name, values in daily_values.items():
        if values:
            if metric_name == "garmin_resting_heart_rate_bpm":
                metrics[metric_name] = sum(values) / len(values)
            else:
                metrics[metric_name] = sum(values)

    activity_count = 0
    activity_totals = {"distance": 0.0, "duration": 0.0, "calories": 0.0}
    for (payload,) in connection.execute("SELECT payload FROM activities"):
        activity = json.loads(payload)
        activity_count += 1
        for key in activity_totals:
            value = activity.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                activity_totals[key] += value

    metrics.update({
        "garmin_sync_activities_stored": activity_count,
        "garmin_activity_distance_meters_total": activity_totals["distance"],
        "garmin_activity_duration_seconds_total": activity_totals["duration"],
        "garmin_activity_calories_total": activity_totals["calories"],
    })
    return metrics


def store_new_activities(
    client: GarminPersonalApiClient,
    connection: sqlite3.Connection,
    limit: int,
) -> list[dict[str, Any]]:
    new_activities = []
    batch_size = max(limit, 1)
    offset = 0

    while True:
        response = client.search_activities(start=offset, limit=batch_size)
        if isinstance(response, list):
            batch = response
        elif isinstance(response, dict):
            batch = response.get(
                "activityList",
                response.get("activities", response.get("data")),
            )
            if not isinstance(batch, list):
                raise ValueError("Nieoczekiwany format odpowiedzi Garmin activities.")
        else:
            raise ValueError("Nieoczekiwany format odpowiedzi Garmin activities.")
        if not batch:
            break

        found_existing = False
        for item in batch:
            if not isinstance(item, dict):
                raise ValueError("Nieoczekiwany element odpowiedzi Garmin activities.")
            activity: dict[str, Any] = item
            activity_id = activity.get("activityId")
            if activity_id is None:
                continue
            activity_id = str(activity_id)
            cursor = connection.execute(
                "INSERT OR IGNORE INTO activities (activity_id, activity_date, payload) "
                "VALUES (?, ?, ?)",
                (
                    activity_id,
                    activity.get("startTimeLocal") or activity.get("startTimeGMT"),
                    json.dumps(activity, ensure_ascii=False),
                ),
            )
            if cursor.rowcount == 0:
                found_existing = True
                break
            new_activities.append(activity)

        if found_existing or len(batch) < batch_size:
            break
        offset += len(batch)
        time.sleep(0.2)

    return new_activities


def publish_metrics(metrics):
    gateway = os.environ.get("PROMETHEUS_PUSHGATEWAY")
    if not gateway:
        return

    registry = CollectorRegistry()
    for name, value in metrics.items():
        Gauge(name, name.replace("_", " "), registry=registry).set(value)
    try:
        pushadd_to_gateway(gateway, job="garmin-app", registry=registry)
    except Exception as exc:
        print(f"Nie udało się wysłać metryk do Prometheusa ({type(exc).__name__}).", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Pobieranie danych przez Garmin Connect Personal API")
    p.add_argument("--days", type=int, default=90, help="maksymalna liczba dni historii do pobrania w jednym uruchomieniu")
    p.add_argument("--start-date", type=date.fromisoformat, help="początek historii, format YYYY-MM-DD")
    p.add_argument("--out", type=Path, default=Path("garmin_data"))
    p.add_argument("--activities", type=int, default=100, help="rozmiar strony przy pobieraniu aktywności")
    p.add_argument(
        "--download-fit",
        action="store_true",
        help="pobierz archiwum ZIP z plikiem aktywności",
    )
    args = p.parse_args()

    started_at = time.time()
    database = init_database(args.out / "garmin.sqlite3")
    metrics = collect_stored_metrics(database)
    metrics.update({
        "garmin_sync_success": 0,
        "garmin_sync_last_attempt_timestamp_seconds": started_at,
        "garmin_sync_days_requested": args.days,
        "garmin_sync_days_completed": 0,
        "garmin_sync_duration_seconds": 0,
    })

    client = None
    try:
        client = create_api_client(args.out / ".garmin-personal-api-bearer-token.json")
        end_date = date.today() - timedelta(days=1)
        new_activities = store_new_activities(client, database, args.activities)
        database.commit()
        last_date_row = database.execute("SELECT MAX(day) FROM daily_data").fetchone()
        if last_date_row[0]:
            next_date = date.fromisoformat(last_date_row[0]) + timedelta(days=1)
        elif args.start_date:
            next_date = args.start_date
        else:
            oldest_activity = database.execute(
                "SELECT MIN(activity_date) FROM activities WHERE activity_date IS NOT NULL"
            ).fetchone()[0]
            if oldest_activity:
                next_date = date.fromisoformat(oldest_activity[:10])
            else:
                next_date = end_date - timedelta(days=max(args.days - 1, 0))

        days_completed = 0
        current_date = next_date
        while current_date <= end_date and days_completed < args.days:
            day_date = current_date.isoformat()
            stats = client.get_daily_summaries(day_date, day_date)
            sleep = client.get_daily_sleep(day_date)
            heart_rate = client.get_daily_heart_rate(day_date)
            day = {
                "stats": stats,
                "sleep": sleep,
                "heart_rate": heart_rate,
                "steps": client.get_daily_steps(day_date, day_date),
            }
            database.execute(
                "INSERT INTO daily_data (day, payload) VALUES (?, ?) "
                "ON CONFLICT(day) DO UPDATE SET payload = excluded.payload",
                (day_date, json.dumps(day, ensure_ascii=False)),
            )
            save(day, f"day_{day_date}", args.out)
            days_completed += 1
            current_date += timedelta(days=1)

        database.commit()
        save(new_activities, "new_activities", args.out)

        activity_files = 0
        if args.download_fit:
            for activity in new_activities:
                activity_id = activity["activityId"]
                raw = client.download_activity(activity_id)
                path = args.out / f"activity_{activity_id}.zip"
                path.write_bytes(raw)
                activity_files += 1
                print(f"Zapisano: {path}")

        metrics = collect_stored_metrics(database)
        metrics.update({
            "garmin_sync_success": 1,
            "garmin_sync_last_attempt_timestamp_seconds": started_at,
            "garmin_sync_last_success_timestamp_seconds": time.time(),
            "garmin_sync_days_requested": args.days,
            "garmin_sync_days_completed": days_completed,
            "garmin_activity_files_downloaded_last_run": activity_files,
            "garmin_sync_duration_seconds": time.time() - started_at,
        })
        database.execute(
            "INSERT INTO metadata (key, value) VALUES ('last_success', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(metrics["garmin_sync_last_success_timestamp_seconds"]),),
        )
        database.commit()
    except Exception:
        metrics.update({
            "garmin_sync_success": 0,
            "garmin_sync_last_attempt_timestamp_seconds": started_at,
            "garmin_sync_duration_seconds": time.time() - started_at,
        })
        publish_metrics(metrics)
        raise
    finally:
        if client is not None:
            client.close()
        database.close()

    publish_metrics(metrics)


if __name__ == "__main__":
    main()
