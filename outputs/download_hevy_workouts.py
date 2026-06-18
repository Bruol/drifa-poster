#!/usr/bin/env python3
"""Download every Hevy workout for one or more usernames."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.hevyapp.com/user_workouts_paged"
DEFAULT_USERS = ("drifa", "bruol")


def fetch_page(username: str, limit: int, offset: int, token: str) -> Any:
    query = urlencode({"username": username, "limit": limit, "offset": offset})
    request = Request(
        f"{API_URL}?{query}",
        headers={
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {token}",
            "Hevy-Platform": "web",
            "Origin": "https://hevy.com",
            "Referer": "https://hevy.com/",
            "User-Agent": "Mozilla/5.0",
            "X-Api-Key": "shelobs_hevy_web",
            "X-Client-Time": str(time.time()),
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {username}: {details}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Request failed for {username}: {exc}") from exc


def workout_list(page: Any) -> list[Any]:
    if isinstance(page, list):
        return page
    if isinstance(page, dict):
        for key in ("workouts", "data", "items", "results"):
            value = page.get(key)
            if isinstance(value, list):
                return value
    raise RuntimeError(f"Could not find the workout list in response: {page!r}")


def download_user(username: str, limit: int, token: str) -> list[Any]:
    workouts: list[Any] = []
    offset = 0

    while True:
        page_items = workout_list(fetch_page(username, limit, offset, token))
        workouts.extend(page_items)
        print(f"{username}: downloaded {len(workouts)} workouts", flush=True)

        if len(page_items) < limit:
            return workouts
        offset += len(page_items)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usernames", nargs="*", default=DEFAULT_USERS)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    token = os.environ.get("HEVY_BEARER_TOKEN")
    if not token:
        parser.error("Set the HEVY_BEARER_TOKEN environment variable first")
    if args.limit < 1:
        parser.error("--limit must be at least 1")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for username in args.usernames:
        workouts = download_user(username, args.limit, token)
        destination = args.output_dir / f"{username}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(workouts, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        print(f"Saved {len(workouts)} workouts to {destination}")


if __name__ == "__main__":
    main()
