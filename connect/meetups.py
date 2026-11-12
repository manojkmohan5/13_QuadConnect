"""
Meeting up: signing up for a weekend, and acting on the match it brings.
The rules are in connect/matching.py; these are the pages.

    meet      /meet/                    sign up, see your match, or leave
    answer    /matches/<pk>/answer/     accept, decline or check in (POST)
    feedback  /matches/<pk>/feedback/   after checking in: how it went

A student only ever acts on their own place in a match: every lookup below
starts from the signed-in user's MatchParticipant row, so another match's
id is a 404.
"""

from datetime import timedelta

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import matching
from .forms import FeedbackForm, MeetForm
from .models import (
    MatchParticipant,
    MatchRequest,
    MatchStatus,
    ParticipantResponse,
    StudentProfile,
)


def actions(me):
    """What this student can do in their match right now."""
    return {
        "can_answer": matching.can_answer(me),
        "can_check_in": matching.can_check_in(me),
        "check_in_later": timezone.now() < me.match.scheduled_for - matching.CHECK_IN_OPENS,
        "can_give_feedback": matching.can_give_feedback(me),
        "connected": matching.stay_connected(me),
    }


def notice(user):
    """The home page's line about the coming weekend: what to do next, and
    where. None for someone with no profile (base.html asks for one)."""
    profile = StudentProfile.objects.filter(user=user).first()
    if profile is None:
        return None
    week = matching.coming_week()
    me = matching.current_match(profile, week)
    if me is None:
        if MatchRequest.objects.filter(profile=profile, week_start=week).exists():
            text = ("You're signed up for this weekend. You'll be matched as soon as "
                    "someone who shares an interest and a free time signs up.")
        else:
            text = "Meet someone this weekend: sign up for a 1-on-1 or a group."
        return {"text": text, "url": reverse("connect:meet"), "link": "This weekend"}
    match = me.match
    start = timezone.localtime(match.scheduled_for)
    # %-I is glibc-only, so the hour's leading zero is stripped by hand (Windows).
    when = f"{start:%A} {start.strftime('%I:%M %p').lstrip('0')} at {match.location.name}"
    if matching.can_check_in(me):
        text, link = f"Your meetup is now, at {match.location.name}. Check in when you get there.", "Check in"
    elif matching.can_give_feedback(me):
        text, link = "How was your meetup? Tell us, privately.", "Give feedback"
    elif me.response == ParticipantResponse.PENDING:
        text, link = f"You have a match: {when}. Are you in?", "See your match"
    elif match.status == MatchStatus.CONFIRMED:
        text, link = f"Confirmed: {when}.", "See your match"
    else:
        text, link = f"You're in for {when}. Waiting for the others to answer.", "See your match"
    return {"text": text, "url": match.get_absolute_url(), "link": link}


def meet(request):
    """The coming weekend for the signed-in student: sign up (1-on-1 or a
    group), wait for a match, see it, or leave. Matching runs on every
    sign-up and leave, so a match can be here on the next page."""
    profile = StudentProfile.objects.for_cards().filter(user=request.user).first()
    week = matching.coming_week()
    context = {"profile": profile, "saturday": week + timedelta(days=5), "sunday": week + timedelta(days=6)}
    if profile is None:  # a page, not a redirect: it says why a profile comes first
        return render(request, "connect/meet.html", context)

    signup = MatchRequest.objects.filter(profile=profile, week_start=week).first()
    if request.method == "POST":
        if "leave" in request.POST:
            if signup:
                matching.leave(profile, week)
                messages.info(request, "You've left this weekend's matching. Sign up again any time before it.")
            return redirect("connect:meet")
        form = MeetForm(request.POST)
        if signup or form.is_valid():  # a second copy of the sign-up changes nothing
            if signup is None:
                matching.sign_up(profile, form.cleaned_data["connection_type"], week)
                if matching.current_match(profile, week):
                    messages.success(request, "You have a match! Accept it below to say you're in.")
                else:
                    messages.success(request, "You're signed up. You'll be matched as soon as someone "
                                              "who shares an interest and a free time signs up.")
            return redirect("connect:meet")
    else:
        form = MeetForm(initial={"connection_type": profile.preferred_connection})

    me = matching.current_match(profile, week)
    slots = matching.weekend_slots(week)
    free = {(s.weekday, s.time_block) for s in profile.availability_slots.all()}
    context.update({
        "signup": signup,
        "form": form,
        "me": me,
        "actions": actions(me) if me else None,
        "others": me.match.participants.exclude(pk=me.pk).select_related("profile") if me else [],
        "no_time_left": not any((s.day, s.block) in free for s in slots),
        "called_off": me is None and MatchParticipant.objects.filter(
            profile=profile, match__week_start=week, match__status=MatchStatus.CANCELLED,
        ).exclude(response=ParticipantResponse.DECLINED).exists(),
    })
    return render(request, "connect/meet.html", context)


def _mine(request, pk):
    """The signed-in student's place in match pk, or 404."""
    return get_object_or_404(MatchParticipant.objects.select_related("match", "match__location"),
                             match_id=pk, profile__user=request.user)


@require_POST
def answer(request, pk):
    """Accept, decline or check in, then back to the page the button was on."""
    me = _mine(request, pk)
    action = request.POST.get("action")
    if action in ("accept", "decline") and matching.can_answer(me):
        matching.respond(me, accept=action == "accept")
        me.match.refresh_from_db()
        if action == "decline":
            messages.info(request, "You declined. If someone else fits, you'll be matched with them.")
        elif me.match.status == MatchStatus.CONFIRMED:
            messages.success(request, "Everyone's in: your meetup is confirmed.")
        else:
            messages.success(request, "You're in. The meetup is confirmed once everyone has answered.")
    elif action == "check_in" and matching.can_check_in(me):
        matching.check_in(me)
        messages.success(request, "You're checked in. Enjoy, and tell us how it went afterwards.")
    else:  # a page left open too long, or a second click
        messages.info(request, "That can't be done any more. Here is where things stand.")
    back = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        back = me.match.get_absolute_url()
    return redirect(back)


def feedback(request, pk):
    """How the meetup went (Screen 9): once, after checking in. Private."""
    me = _mine(request, pk)
    if not matching.can_give_feedback(me):
        messages.info(request, "Feedback opens once you've checked in, and you give it once.")
        return redirect(me.match)
    form = FeedbackForm(request.POST or None)
    if form.is_valid():
        given = form.save(commit=False)
        given.participant = me
        try:
            given.save()
        except IntegrityError:  # a second click: the first one saved it
            pass
        messages.success(request, "Thank you. Your feedback is private: no one in the match sees it.")
        return redirect(me.match)
    return render(request, "connect/feedback_form.html", {"form": form, "match": me.match})
