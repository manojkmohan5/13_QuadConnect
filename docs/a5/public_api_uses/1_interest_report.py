"""
Use 1 of the QuadConnect public API: a command-line report (P1-A5 Part 3.4).

    python docs/a5/public_api_uses/1_interest_report.py [API URL]

A club organizer or student-life office could run this to see which
interests and student organizations QuadConnect students pick most, without
any access to the site's private pages. It reads the one public endpoint,
/api/summary/ (no login, JSON), and prints:

  - the share of all picks that are hobbies versus student organizations;
  - the five most picked interests;
  - the interests only one student picked, which are candidates for
    merging or promoting.

The checks at the end stop the script if the API's shape ever changes.
"""

import sys
from collections import defaultdict

import requests

API = "https://manojkmohan43.pythonanywhere.com/api/summary/"


def main(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    rows = response.json()  # [{"category": ..., "count": ..., "type": ...}, ...]

    picks_by_type = defaultdict(int)
    interests_by_type = defaultdict(int)
    for row in rows:
        picks_by_type[row["type"]] += row["count"]
        interests_by_type[row["type"]] += 1
    total = sum(picks_by_type.values())

    print(f"GET {url}  ->  HTTP {response.status_code}, {len(rows)} interests, {total} picks\n")
    print(f"{'Type':34} {'Interests':>9} {'Picks':>6} {'Share':>6} {'Avg/interest':>13}")
    for kind, picks in sorted(picks_by_type.items(), key=lambda item: -item[1]):
        n = interests_by_type[kind]
        print(f"{kind:34} {n:>9} {picks:>6} {picks / total:>6.0%} {picks / n:>13.2f}")

    print("\nTop 5 interests")
    for rank, row in enumerate(sorted(rows, key=lambda r: (-r["count"], r["category"]))[:5], 1):
        print(f"  {rank}. {row['category']:28} {row['count']} students  ({row['type']})")

    singles = sorted(r["category"] for r in rows if r["count"] == 1)
    print(f"\nPicked by only one student ({len(singles)}): {', '.join(singles)}")

    # The API's contract: one row per interest, three fields each.
    if any(set(r) != {"category", "count", "type"} for r in rows):
        raise SystemExit("The API sent a row with unexpected fields.")
    if len({r["category"] for r in rows}) != len(rows):
        raise SystemExit("The API sent the same interest twice.")
    print("\nChecks passed: one row per interest, three fields each.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else API)
