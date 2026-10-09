"""
Icebreaker trivia for a match (P1-A4 Part 2: an external, keyless API).

    GET /api/icebreakers/?match=<id>   the result as JSON
    GET /matches/<id>/icebreakers/     the same result as a page

The questions come from the Open Trivia Database (opentdb.com), which is
free and needs no key. For one match:

  1. our data: the interests the match's members picked (members who
     declined the match are left out);
  2. analytics: each interest maps to a trivia category, and each category
     scores the number of members it covers. The topic is the category
     shared by the most members (at least two; a tie is broken at random,
     so a reload can change it), or General Knowledge if none is shared;
  3. external data: five easy multiple-choice questions on that topic;
  4. processing: the HTML entities Open Trivia DB sends are decoded, and
     each question's choices are sorted, so the answer is not always first.

Nothing from Open Trivia DB is saved. A category's questions stay in memory
for 5 seconds at most (see fetch_questions), then the next request fetches
new ones. Only counts leave through the API, never names, NetIDs or
check-in codes.

Open Trivia DB allows one request every 5 seconds per IP address and
answers a faster one with HTTP 429. Our client then gets 503 with
Retry-After; any other failure upstream is a 502, or 504 for a timeout.
"""

import html
import logging
import random
from collections import Counter, defaultdict

import requests
from django import forms
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .api import JSON_PARAMS, _bad_params
from .models import Match, ParticipantResponse, ProfileInterest

logger = logging.getLogger(__name__)

TRIVIA_URL = "https://opentdb.com/api.php"
QUESTIONS = 5
RETRY_AFTER = 5  # seconds: Open Trivia DB's limit per IP address
SOURCE = {"name": "Open Trivia Database", "url": "https://opentdb.com/",
          "license": "CC BY-SA 4.0"}

# Interest name -> Open Trivia DB category (id, name), from
# https://opentdb.com/api_category.php. An interest that is not listed, or
# is renamed in the admin, just does not steer the topic.
GENERAL_KNOWLEDGE = (9, "General Knowledge")
TRIVIA_CATEGORIES = {
    "Art": (25, "Art"),
    "Photography": (25, "Art"),
    "Basketball": (21, "Sports"),
    "Fitness": (21, "Sports"),
    "Gaming": (15, "Video Games"),
    "UIUC Esports": (15, "Video Games"),
    "Movies": (11, "Film"),
    "Music": (12, "Music"),
    "Outdoors": (17, "Science & Nature"),
    "UIUC Pre-Med Society": (17, "Science & Nature"),
    "Reading": (10, "Books"),
    "Technology": (18, "Computers"),
    "Illini Robotics": (18, "Computers"),
    "Travel": (22, "Geography"),
    "Illinois Student Government": (24, "Politics"),
}

BUSY = "Open Trivia DB is busy right now."


class TriviaUnavailable(Exception):
    """Open Trivia DB could not supply questions. status is what we answer."""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


# --- 1-2: our data and the analytics ------------------------------------------


def common_ground(match):
    """What the match's members share, and the trivia topic it points to.

    {"members": 4,
     "interests": [{"interest": "Gaming", "members": 3, "trivia_category": "Video Games"}, ...],
     "topic": {"category_id": 15, "category": "Video Games", "members": 3,
               "because": ["Gaming", "UIUC Esports"]}}
    """
    members = match.participants.exclude(response=ParticipantResponse.DECLINED)
    picks = list(ProfileInterest.objects.filter(profile__in=members.values("profile"))
                 .values_list("profile_id", "interest__name"))

    per_interest = Counter(name for _, name in picks)
    covered, because = defaultdict(set), defaultdict(set)  # category -> members, interests
    for profile_id, name in picks:
        if name in TRIVIA_CATEGORIES:
            covered[TRIVIA_CATEGORIES[name]].add(profile_id)
            because[TRIVIA_CATEGORIES[name]].add(name)

    category = GENERAL_KNOWLEDGE
    top = max((len(m) for m in covered.values()), default=0)
    if top >= 2:  # trivia one member likes and the others do not is no icebreaker
        category = random.choice(sorted(c for c, m in covered.items() if len(m) == top))  # noqa: S311 - not a secret
    return {
        "members": members.count(),
        "interests": [{"interest": name, "members": n,
                       "trivia_category": TRIVIA_CATEGORIES.get(name, (None, None))[1]}
                      for name, n in sorted(per_interest.items(), key=lambda i: (-i[1], i[0]))],
        "topic": {"category_id": category[0], "category": category[1],
                  "members": len(covered[category]), "because": sorted(because[category])},
    }


# --- 3-4: the external API and the processing -----------------------------------


def fetch_questions(category_id):
    """Five easy multiple-choice questions from one Open Trivia DB category,
    or TriviaUnavailable saying why not. A category's questions are reused
    for RETRY_AFTER seconds, Open Trivia DB's own limit, so a quick reload
    gets them again instead of being turned away. Failures are not kept."""
    return cache.get_or_set(f"trivia:{category_id}", lambda: _ask(category_id), RETRY_AFTER)


def _ask(category_id):
    try:
        response = requests.get(TRIVIA_URL, params={
            "amount": QUESTIONS, "category": category_id,
            "difficulty": "easy", "type": "multiple",
        }, timeout=5)
        response.raise_for_status()
    except requests.Timeout as error:
        raise TriviaUnavailable("Open Trivia DB did not answer within 5 seconds.", 504) from error
    except requests.HTTPError as error:
        if error.response.status_code == 429:
            raise TriviaUnavailable(BUSY, 503) from error
        raise TriviaUnavailable(
            f"Open Trivia DB answered with an error (HTTP {error.response.status_code}).") from error
    except requests.RequestException as error:  # DNS, refused connection, proxy
        raise TriviaUnavailable("Could not reach Open Trivia DB.") from error

    try:
        data = response.json()
        code = data["response_code"]
        if code == 5:  # the rate limit, when it comes with HTTP 200
            raise TriviaUnavailable(BUSY, 503)
        if code != 0:
            raise TriviaUnavailable(f"Open Trivia DB had no questions (response code {code}).")
        return [_question(q) for q in data["results"]]
    except (ValueError, KeyError, TypeError) as error:  # not JSON, or not this shape
        raise TriviaUnavailable("Open Trivia DB sent a reply we could not read.") from error


def _question(raw):
    answer = html.unescape(raw["correct_answer"])
    choices = [answer, *(html.unescape(a) for a in raw["incorrect_answers"])]
    return {"question": html.unescape(raw["question"]),
            "choices": sorted(choices, key=str.casefold),
            "answer": answer}


# --- Views ----------------------------------------------------------------------


class IcebreakerQuery(forms.Form):
    match = forms.IntegerField(min_value=1, error_messages={
        "required": "Add the id of a match, e.g. ?match=2.",
        "invalid": "Use the match's id, a whole number, e.g. match=2.",
        "min_value": "Use the match's id, a whole number, e.g. match=2.",
    })


@require_GET
def icebreakers_api(request):
    """GET /api/icebreakers/?match=<id> - trivia for one match, as JSON."""
    query = IcebreakerQuery(request.GET)
    if not query.is_valid():
        return _bad_params(query)
    match = Match.objects.filter(pk=query.cleaned_data["match"]).first()
    if match is None:
        return JsonResponse({"error": f"There is no match with id {query.cleaned_data['match']}."},
                            status=404, json_dumps_params=JSON_PARAMS)

    found = common_ground(match)
    try:
        questions = fetch_questions(found["topic"]["category_id"])
    except TriviaUnavailable as error:
        logger.warning("Icebreakers for match %s: %s (%r)", match.pk, error, error.__cause__)
        response = JsonResponse({"error": str(error)}, status=error.status,
                                json_dumps_params=JSON_PARAMS)
        if error.status == 503:
            response["Retry-After"] = str(RETRY_AFTER)
        return response

    return JsonResponse({
        "match": {"id": match.pk, "connection_type": match.connection_type,
                  "status": match.status,
                  "url": request.build_absolute_uri(match.get_absolute_url())},
        **found,
        "questions": questions,
        "source": SOURCE,
    }, json_dumps_params=JSON_PARAMS)


@require_GET
def icebreakers_page(request, pk):
    """GET /matches/<id>/icebreakers/ - the same result, as a page. If Open
    Trivia DB fails, the page still shows what the group has in common."""
    match = get_object_or_404(Match, pk=pk)
    context = {"match": match, **common_ground(match)}
    try:
        context["questions"] = fetch_questions(context["topic"]["category_id"])
    except TriviaUnavailable as error:
        logger.warning("Icebreakers for match %s: %s (%r)", match.pk, error, error.__cause__)
        context["error"] = str(error)
    return render(request, "connect/icebreakers.html", context)
