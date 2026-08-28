"""Load a GitHub contribution calendar, either from the API or synthesised."""

from __future__ import annotations

import json
import random
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


@dataclass(frozen=True)
class Day:
    """One square of the calendar."""

    day: date
    count: int
    level: int


@dataclass(frozen=True)
class Calendar:
    """Weeks as columns; each column has 7 slots, Sunday first.

    Slots outside the calendar range (the ragged first and last weeks) are None.
    """

    weeks: list[list[Day | None]]
    total: int

    @property
    def ore(self) -> list[Day]:
        return [d for week in self.weeks for d in week if d and d.level > 0]


def _row(day: date) -> int:
    """Calendar row for a date, Sunday = 0 .. Saturday = 6."""
    return day.isoweekday() % 7


def _to_calendar(raw_weeks: list[dict], total: int) -> Calendar:
    weeks: list[list[Day | None]] = []
    for raw in raw_weeks:
        column: list[Day | None] = [None] * 7
        for entry in raw["contributionDays"]:
            day = date.fromisoformat(entry["date"])
            column[_row(day)] = Day(
                day=day,
                count=entry["contributionCount"],
                level=LEVELS.get(entry["contributionLevel"], 0),
            )
        weeks.append(column)
    return Calendar(weeks=weeks, total=total)


def fetch(login: str, token: str, *, timeout: int = 30) -> Calendar:
    """Read the last year of contributions for `login` from GitHub's GraphQL API."""
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-miner",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    if payload.get("errors"):
        messages = "; ".join(e.get("message", "?") for e in payload["errors"])
        raise RuntimeError(f"GitHub GraphQL error: {messages}")

    user = (payload.get("data") or {}).get("user")
    if not user:
        raise RuntimeError(f"No such GitHub user: {login}")

    calendar = user["contributionsCollection"]["contributionCalendar"]
    return _to_calendar(calendar["weeks"], calendar["totalContributions"])


def demo(*, weeks: int = 53, seed: int = 7) -> Calendar:
    """Build a plausible calendar without touching the network.

    Useful for previewing changes to the renderer offline.
    """
    rng = random.Random(seed)
    end = date.today()
    start = end - timedelta(days=weeks * 7 - 1)
    start -= timedelta(days=_row(start))

    counts: list[tuple[date, int]] = []
    streak = 0
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        if streak > 0:
            streak -= 1
            count = rng.randint(1, 14)
        elif rng.random() < 0.42:
            streak = rng.randint(2, 9)
            count = rng.randint(1, 8)
        else:
            count = 0
        if day.isoweekday() >= 6 and rng.random() < 0.5:
            count = 0
        counts.append((day, count))

    ceiling = max((c for _, c in counts), default=0) or 1
    columns: list[list[Day | None]] = []
    for day, count in counts:
        if _row(day) == 0 or not columns:
            columns.append([None] * 7)
        level = 0 if count == 0 else min(4, 1 + int(3 * count / ceiling))
        columns[-1][_row(day)] = Day(day=day, count=count, level=level)

    return Calendar(weeks=columns, total=sum(c for _, c in counts))
