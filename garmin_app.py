#!/usr/bin/env python3
"""Pobieranie danych z Garmin Connect (biblioteka garminconnect)."""
import argparse
import getpass
import json
import os
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin

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


def main():
    p = argparse.ArgumentParser(description="Pobieranie danych z Garmin Connect")
    p.add_argument("--days", type=int, default=7, help="liczba ostatnich dni")
    p.add_argument("--out", type=Path, default=Path("garmin_data"))
    p.add_argument("--activities", type=int, default=10, help="liczba aktywności")
    p.add_argument("--download-fit", action="store_true", help="pobierz pliki FIT aktywności")
    args = p.parse_args()

    client = login()
    today = date.today()

    for i in range(args.days):
        d = (today - timedelta(days=i)).isoformat()
        day = {
            "stats": client.get_stats(d),
            "sleep": client.get_sleep_data(d),
            "heart_rate": client.get_heart_rates(d),
            "steps": client.get_steps_data(d),
        }
        save(day, f"day_{d}", args.out)

    activities = client.get_activities(0, args.activities)
    save(activities, "activities", args.out)

    if args.download_fit:
        for a in activities:
            aid = a["activityId"]
            raw = client.download_activity(aid, dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL)
            f = args.out / f"activity_{aid}.zip"
            f.write_bytes(raw)
            print(f"Zapisano: {f}")


if __name__ == "__main__":
    main()
