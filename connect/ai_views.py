"""
Views for the two AI features (P1-A6 Part 2).

    /ai/profile-assistant/        local Hugging Face model: free text -> preferences
    /matches/<id>/ai-welcome/     hybrid: local model + external API -> welcome message

Both pages need a login (the site-wide middleware), generate only on POST
(so a link or a prefetch never starts a model run), and are rate-limited per
user because a model call costs seconds of CPU or a paid API request.
Nothing the student types or the model answers is stored.
"""

import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from . import ai_api, ai_local
from .forms import MatchNoteForm, ProfileIntroForm
from .models import ConversationStyle, GroupPreference, Interest, Match, ProfileInterest

logger = logging.getLogger(__name__)

RATE_LIMIT = 6        # model/API calls per user ...
RATE_WINDOW = 60      # ... per this many seconds


def rate_limited(user, scope):
    """True if this user has used up their calls for the current window."""
    key = f"ai-rate:{scope}:{user.pk}"
    cache.add(key, 0, RATE_WINDOW)
    try:
        return cache.incr(key) > RATE_LIMIT
    except ValueError:  # the key expired between add() and incr()
        cache.set(key, 1, RATE_WINDOW)
        return False


def _too_many(request, template, context):
    context["error"] = (f"That is more than {RATE_LIMIT} requests a minute. "
                        f"Wait {RATE_WINDOW} seconds and try again.")
    return render(request, template, context, status=429)


def _members_per_interest(names):
    """How many students picked each of these interests: counts only, never who."""
    counts = dict(ProfileInterest.objects.filter(interest__name__in=names)
                  .values_list("interest__name").annotate(n=Count("profile", distinct=True)))
    return [{"name": name, "students": counts.get(name, 0)} for name in names]


@require_http_methods(["GET", "POST"])
def profile_assistant(request):
    """Write a few sentences, get the preferences our onboarding form stores."""
    template = "connect/ai_profile_assistant.html"
    context = {"model": settings.LOCAL_LLM_MODEL, "catalogue_size": Interest.objects.filter(is_active=True).count()}
    if request.method == "GET":
        return render(request, template, {**context, "form": ProfileIntroForm()})

    form = ProfileIntroForm(request.POST)
    context["form"] = form
    if not form.is_valid():
        return render(request, template, context, status=400)
    if rate_limited(request.user, "local"):
        return _too_many(request, template, context)

    result = ai_local.extract_preferences(form.cleaned_data["text"])
    result["interest_rows"] = _members_per_interest(result["interests"])
    result["style_label"] = dict(ConversationStyle.choices)[result["conversation_style"]]
    result["group_label"] = dict(GroupPreference.choices)[result["group_preference"]]
    return render(request, template, {**context, "result": result})


@require_http_methods(["GET", "POST"])
def match_welcome(request, pk):
    """Hybrid pipeline: our data + the local model + an external API."""
    match = get_object_or_404(Match.objects.select_related("location", "suggested_activity"), pk=pk)
    template = "connect/ai_match_welcome.html"
    context = {"match": match}
    if request.method == "GET":
        return render(request, template, {**context, "form": MatchNoteForm()})

    form = MatchNoteForm(request.POST)
    context["form"] = form
    if not form.is_valid():
        return render(request, template, context, status=400)
    if rate_limited(request.user, "welcome"):
        return _too_many(request, template, context)

    preferences = None
    note = ai_local.clean_text(form.cleaned_data["note"])
    if note:
        preferences = ai_local.extract_preferences(note)
    context["preferences"] = preferences
    context["welcome"] = ai_api.welcome_for_match(match, preferences)
    return render(request, template, context)
