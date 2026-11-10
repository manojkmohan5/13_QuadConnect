"""
The measurements behind README_AI.md, Part 1 (P1-A9): interests placed by meaning.

    python manage.py download_ai_model     # once: both models into the Hugging Face cache
    python docs/a9_part1/measure.py

1. calibration.csv: the embedding model's closest interest, and the next one, for
   words the language model might write in place of an interest. 34 should be
   placed and 36 should not (the calibration set, which MEANING_MIN and
   MEANING_LEAD in connect/ai_search.py were fitted to), then 20 and 25 more that
   played no part in choosing them (the held-out set).
2. requests.csv and requests.json: Part 3's 20 evaluation requests
   (docs/a9_evaluation/), each sent through the /search/ask/ view with the real
   models, once with matching by meaning off and once with it on. Each row holds
   the model's raw reply, so a missing interest can be traced to the model or to
   the allow-list.
3. summary.json: the counts, the times and the machine.

It runs on a copy of db.sqlite3 in a temporary folder, so the committed database
gets no login session, and it clears the cache before every request, so every
answer comes from the model.
"""

import csv
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
_db = Path(tempfile.mkdtemp()) / "db.sqlite3"
shutil.copy(ROOT / "db.sqlite3", _db)
os.environ["DJANGO_DB_PATH"] = str(_db)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "quadconnect.settings.development")
os.environ["AI_LOCAL_ENABLED"] = "1"

import django  # noqa: E402  (after the environment above)

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.core.cache import cache  # noqa: E402
from django.test import Client, override_settings  # noqa: E402
from django.test.utils import setup_test_environment  # noqa: E402
from django.urls import reverse  # noqa: E402

from connect import ai_search  # noqa: E402

SHOULD_MATCH = {  # calibration set: a word the model might write -> the interest it means
    "Painting": "Art", "Drawing": "Art", "Sketching": "Art", "Tech": "Technology", "Coding": "Technology",
    "Programming": "Technology", "Hiking": "Outdoors", "Camping": "Outdoors", "Photos": "Photography",
    "Photo": "Photography", "Films": "Movies", "Cinema": "Movies", "Gym": "Fitness", "Workout": "Fitness",
    "Video games": "Gaming", "Gamers": "Gaming", "Books": "Reading", "Literature": "Reading", "Cooking": "Food",
    "Hoops": "Basketball", "Concerts": "Music", "Guitar": "Music", "Traveling": "Travel", "Yoga": "Fitness",
    "Premed": "UIUC Pre-Med Society", "Medicine": "UIUC Pre-Med Society", "Robots": "Illini Robotics",
    "Volunteering": "Habitat for Humanity UIUC", "Journalism": "Illini Media", "Video gaming": "Gaming",
    "Running": "Fitness", "Nature": "Outdoors", "Photographers": "Photography", "Movie": "Movies",
}
SHOULD_NOT = [  # calibration set: words that name no interest (filters, invented keys, other things)
    "joke", "weather", "Champaign", "NetID", "email", "password", "student_data", "location", "Sunday",
    "morning", "quiet", "friends", "students", "people", "hangout", "Coffee", "Engineering", "Psychology",
    "Chess", "Knitting", "SQUAD", "FRIEND", "Grainger", "admin", "Social", "one-on-one", "Board games",
    "Campus walk", "Study", "abc123", "Business school", "Dancing", "Sports", "Anime", "Science", "Math",
]
HELD_OUT_MATCH = {
    "Artwork": "Art", "Painter": "Art", "Songs": "Music", "Novels": "Reading", "Baking": "Food",
    "Lifting": "Fitness", "Computers": "Technology", "Trips": "Travel", "Cameras": "Photography",
    "Gamer": "Gaming", "Readers": "Reading", "Backpacking": "Outdoors", "Movies and TV": "Movies",
    "Basketball fans": "Basketball", "Weightlifting": "Fitness", "Musicians": "Music", "Foodies": "Food",
    "Photographing": "Photography", "Esport": "UIUC Esports", "Robotics club": "Illini Robotics",
}
HELD_OUT_NOT = [
    "Tuesday", "evening", "outgoing", "shy", "Gies", "College of Media", "email address", "phone", "hello",
    "everyone", "club", "meetup", "UIUC", "Illinois", "politics", "religion", "dating", "homework", "majors",
    "freshman", "dorm", "lunch", "afternoon", "group", "Liberal Arts",
]
KEYS = ("college", "connection", "day", "time", "energy")


def calibration(interests):
    """One row per word: its closest interest and the next one, and what was placed."""
    rows = []
    sets = [("calibration", SHOULD_MATCH, SHOULD_NOT), ("held-out", HELD_OUT_MATCH, HELD_OUT_NOT)]
    for name, match, nothing in sets:
        words = [*match, *nothing]
        scores = ai_search.embed_similarities(words, interests)
        for word, row in zip(words, scores, strict=True):
            (best, closest), (second, runner_up) = sorted(zip(map(float, row), interests, strict=True),
                                                          reverse=True)[:2]
            expected = match.get(word, "")
            # One word at a time: match_by_meaning() compares at most 8 words, as many as an answer may hold.
            got = ai_search.match_by_meaning([word], interests).get(word, "")
            outcome = ("right" if got == expected else "wrong") if got else ("left out" if expected else "right")
            rows.append({"set": name, "word": word, "expected": expected, "closest": closest,
                         "similarity": round(best, 3), "runner_up": runner_up, "runner_up_similarity": round(second, 3),
                         "lead": round(best - second, 3), "placed": got, "outcome": outcome})
    return rows


def verdict(expected, got):
    """Part 3's verdict: Exact, or what is missing, extra or wrong."""
    problems = []
    want, have = set(expected.get("interests", [])), set(got.get("interests", []))
    problems += [f"missing interest: {name}" for name in sorted(want - have)]
    problems += [f"extra interest: {name}" for name in sorted(have - want)]
    for key in KEYS:
        if key in expected and key not in got:
            problems.append(f"missing {key}: {expected[key]}")
        elif key in got and key not in expected:
            problems.append(f"extra {key}: {got[key]}")
        elif key in got and got[key] != expected[key]:
            problems.append(f"wrong {key}: {got[key]}")
    return "; ".join(problems) or "Exact"


def main():
    setup_test_environment()  # keeps each response's context, so the answer is read, not scraped
    client = Client()
    client.force_login(User.objects.get(username="tester"))
    url = reverse("connect:student-ask")
    interests, _ = ai_search.vocabulary()
    tests = [row for row in json.loads((ROOT / "docs" / "a9_evaluation" / "after_results.json").read_text())
             if row["id"] != "T01_REPEAT"]

    print(f"Loading {settings.AI_LOCAL_MODEL} and {settings.AI_EMBED_MODEL} ...")
    started = time.perf_counter()
    client.get(url, {"q": "warm up the models"})
    ai_search.embed_similarities(["warm up"], interests)
    load_seconds = time.perf_counter() - started

    rows = calibration(interests)
    with (HERE / "calibration.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    embed_ms = []
    for _ in range(50):
        started = time.perf_counter()
        ai_search.match_by_meaning(["Painting"], interests)
        embed_ms.append((time.perf_counter() - started) * 1000)

    replies, real_generate = [], ai_search.generate_reply

    def recording_generate(messages):
        reply = real_generate(messages)
        replies.append(reply.strip())
        return reply

    ai_search.generate_reply = recording_generate
    results = []
    for test in tests:
        for mode, enabled in (("off", False), ("on", True)):
            cache.clear()
            replies.clear()
            with override_settings(AI_EMBED_ENABLED=enabled):
                started = time.perf_counter()
                response = client.get(url, {"q": test["request"]})
                wall = time.perf_counter() - started
            answer = response.context["answer"]
            found = response.context["students"]
            results.append({
                "id": test["id"], "request": test["request"], "matching_by_meaning": mode,
                "expected_filters": test["expected_filters"], "model_replies": list(replies),
                "filters": answer["filters"], "by_meaning": answer["by_meaning"],
                "understood_as": response.context["understood"], "read_by": answer["source"],
                "note": answer["note"], "students_found": len(found) if answer["filters"] else None,
                "app_seconds": answer["seconds"], "wall_seconds": round(wall, 3),
                "verdict": verdict(test["expected_filters"], answer["filters"]), "http_status": response.status_code,
            })
            print(f"{test['id']:4} {mode:3} {results[-1]['verdict'][:60]:60} {answer['seconds']:5.1f} s")
    ai_search.generate_reply = real_generate

    (HERE / "requests.json").write_text(json.dumps(results, indent=2) + "\n")
    with (HERE / "requests.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows({key: json.dumps(value) if isinstance(value, dict | list) else value
                          for key, value in row.items()} for row in results)

    def counts(mode):
        mine = [row for row in results if row["matching_by_meaning"] == mode]
        return {"exact": sum(row["verdict"] == "Exact" for row in mine),
                "missing_interest": sum("missing interest" in row["verdict"] for row in mine),
                "extra_or_wrong": sum(("extra" in row["verdict"]) or ("wrong" in row["verdict"]) for row in mine),
                "read_by_model": sum(row["read_by"] == "model" for row in mine),
                "placed_by_meaning": sum(bool(row["by_meaning"]) for row in mine),
                "median_app_seconds": round(statistics.median(row["app_seconds"] for row in mine), 2),
                "median_wall_seconds": round(statistics.median(row["wall_seconds"] for row in mine), 3)}

    def tally(name):
        mine = [row for row in rows if row["set"] == name]
        return {"should_place": sum(bool(row["expected"]) for row in mine),
                "placed_right": sum(row["outcome"] == "right" and bool(row["expected"]) for row in mine),
                "left_out": sum(row["outcome"] == "left out" for row in mine),
                "should_not": sum(not row["expected"] for row in mine),
                "placed_wrong": sum(row["outcome"] == "wrong" for row in mine)}

    summary = {
        "language_model": settings.AI_LOCAL_MODEL, "embedding_model": settings.AI_EMBED_MODEL,
        "meaning_min": ai_search.MEANING_MIN, "meaning_lead": ai_search.MEANING_LEAD,
        "calibration": tally("calibration"), "held_out": tally("held-out"),
        "requests_off": counts("off"), "requests_on": counts("on"),
        "first_request_with_model_loads_seconds": round(load_seconds, 1),
        "match_by_meaning_one_word_ms": {"median": round(statistics.median(embed_ms), 1),
                                         "max": round(max(embed_ms), 1)},
        "machine": {"platform": platform.platform(), "processor": platform.processor(),
                    "python": platform.python_version()},
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
