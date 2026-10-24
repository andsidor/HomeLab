#!/usr/bin/env python3
"""Pobieranie danych z Garmin Connect (biblioteka garminconnect)."""
import argparse
import getpass
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin
from prometheus_client import CollectorRegistry, Gauge, pushadd_to_gateway

TOKEN_DIR = Path.home() / ".garminconnect"


def login() -> Garmin:
    # Najpierw zapisane tokeny, potem logowanie danymi z env/promptu.
    try:
        client = Garmin()
        client.login(str(TOKEN_DIR))
        return client
    except Exception as exc:
        print(f"Brak ważnych tokenów ({type(exc).__name__}), logowanie hasłem.")
    email = os.environ.get("GARMIN_EMAIL") or input("Email: ")
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Hasło: ")
    client = Garmin(email, password, prompt_mfa=lambda: input("Kod MFA: "))
    client.login(str(TOKEN_DIR))
    return client


def save(data, name: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Zapisano: {path}")


def metric_number(data, keys):
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
    p = argparse.ArgumentParser(description="Pobieranie danych z Garmin Connect")
    p.add_argument("--days", type=int, default=7, help="liczba ostatnich dni")
    p.add_argument("--out", type=Path, default=Path("garmin_data"))
    p.add_argument("--activities", type=int, default=10, help="liczba aktywności")
    p.add_argument("--download-fit", action="store_true", help="pobierz pliki FIT aktywności")
    args = p.parse_args()

    started_at = time.time()
    days_completed = 0
    activities = []
    daily_values = {
        "garmin_steps_total": [],
        "garmin_distance_meters_total": [],
        "garmin_active_calories_total": [],
        "garmin_sleep_duration_seconds_total": [],
        "garmin_resting_heart_rate_bpm": [],
    }
    metrics = {
        "garmin_sync_success": 0,
        "garmin_sync_last_attempt_timestamp_seconds": started_at,
        "garmin_sync_days_requested": args.days,
        "garmin_steps_total": 0,
        "garmin_distance_meters_total": 0,
        "garmin_active_calories_total": 0,
        "garmin_sleep_duration_seconds_total": 0,
        "garmin_resting_heart_rate_bpm": 0,
        "garmin_sync_days_completed": 0,
        "garmin_sync_activities_total": 0,
        "garmin_activity_distance_meters_total": 0,
        "garmin_activity_duration_seconds_total": 0,
        "garmin_activity_calories_total": 0,
        "garmin_fit_files_downloaded_total": 0,
        "garmin_sync_duration_seconds": 0,
    }

    try:
        client = login()
        today = date.today()

        for day_offset in range(args.days):
            day_date = (today - timedelta(days=day_offset)).isoformat()
            stats = client.get_stats(day_date)
            sleep = client.get_sleep_data(day_date)
            heart_rate = client.get_heart_rates(day_date)
            day = {
                "stats": stats,
                "sleep": sleep,
                "heart_rate": heart_rate,
                "steps": client.get_steps_data(day_date),
            }
            save(day, f"day_{day_date}", args.out)
            days_completed += 1

            for metric_name, source, keys in (
                ("garmin_steps_total", stats, ("totalSteps",)),
                ("garmin_distance_meters_total", stats, ("totalDistanceMeters",)),
                ("garmin_active_calories_total", stats, ("activeKilocalories", "activeCalories")),
                ("garmin_sleep_duration_seconds_total", sleep, ("sleepTimeSeconds",)),
                ("garmin_resting_heart_rate_bpm", heart_rate, ("restingHeartRate",)),
            ):
                value = metric_number(source, keys)
                if value is not None:
                    daily_values[metric_name].append(value)

        activities = client.get_activities(0, args.activities)
        save(activities, "activities", args.out)

        fit_files = 0
        if args.download_fit:
            for activity in activities:
                activity_id = activity["activityId"]
                raw = client.download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)
                path = args.out / f"activity_{activity_id}.zip"
                path.write_bytes(raw)
                fit_files += 1
                print(f"Zapisano: {path}")

        for metric_name, values in daily_values.items():
            if values:
                if metric_name == "garmin_resting_heart_rate_bpm":
                    metrics[metric_name] = sum(values) / len(values)
                else:
                    metrics[metric_name] = sum(values)

        metrics.update({
            "garmin_sync_success": 1,
            "garmin_sync_last_success_timestamp_seconds": time.time(),
            "garmin_sync_days_completed": days_completed,
            "garmin_sync_activities_total": len(activities),
            "garmin_activity_distance_meters_total": activity_total(activities, "distance"),
            "garmin_activity_duration_seconds_total": activity_total(activities, "duration"),
            "garmin_activity_calories_total": activity_total(activities, "calories"),
            "garmin_fit_files_downloaded_total": fit_files,
            "garmin_sync_duration_seconds": time.time() - started_at,
        })
    except Exception:
        metrics.update({
            "garmin_sync_success": 0,
            "garmin_sync_days_completed": days_completed,
            "garmin_sync_activities_total": len(activities),
            "garmin_sync_duration_seconds": time.time() - started_at,
        })
        publish_metrics(metrics)
        raise

    publish_metrics(metrics)


if __name__ == "__main__":
    main()
