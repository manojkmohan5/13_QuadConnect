"""
Plans: a student posts what they're doing, when and where, and others RSVP.

    plan_list    /plans/                 what's coming up, and your own plans
    plan_create  /plans/new/             post a plan (needs a student profile)
    plan_detail  /plans/<pk>/            who's hosting, who's going, join or leave
    plan_rsvp    /plans/<pk>/rsvp/       join or leave (POST)
    plan_cancel  /plans/<pk>/cancel/     the host calls it off (POST)

The rules, checked on every action rather than only by hiding buttons, since
a page can be left open:

  * A plan is at an approved campus location, between 1 hour and 30 days
    ahead, for 2 to 50 people (the host included) and no more than the venue
    seats.
  * Anyone with a student profile can join until the plan starts, unless it
    is full or called off. The host is always going and cannot RSVP.
  * Going can be undone until the plan starts. Only the host can call it off.
"""

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import PlanForm
from .models import Plan, PlanRSVP, StudentProfile


class Full(Exception):
    """The last place was taken first."""


def spots_left(plan):
    return plan.capacity - 1 - plan.rsvps.count()  # 1: the host


def state(plan, profile):
    """What this student sees and can do on this plan right now."""
    now = timezone.now()
    going = profile is not None and plan.rsvps.filter(profile=profile).exists()
    is_host = profile is not None and plan.host_id == profile.pk
    open_ = plan.cancelled_at is None and plan.starts_at > now
    left = spots_left(plan)
    return {
        "is_host": is_host,
        "going": going,
        "open": open_,
        "started": plan.starts_at <= now,
        "spots_left": left,
        "can_join": open_ and profile is not None and not is_host and not going and left > 0,
        "can_leave": open_ and going,
        "can_cancel": open_ and is_host,
    }


def join(plan, profile):
    """RSVP, or raise Full. The place is taken first and counted after, so
    two students clicking for the last place at once cannot both get it."""
    with transaction.atomic():
        PlanRSVP.objects.create(plan=plan, profile=profile)
        if spots_left(plan) < 0:
            raise Full  # rolls back this student's row


def _profile(request):
    return StudentProfile.objects.filter(user=request.user).first()


def _with_counts(plans):
    return plans.select_related("host", "location").annotate(going=Count("rsvps") + 1)


def plan_list(request):
    """Upcoming plans everyone can join, then the signed-in student's own."""
    profile = _profile(request)
    upcoming = _with_counts(Plan.objects.filter(cancelled_at__isnull=True, starts_at__gt=timezone.now()))
    mine = []
    if profile:
        # pk__in, not a join on rsvps: a join would make Count("rsvps") count only this student's row.
        going = PlanRSVP.objects.filter(profile=profile).values("plan_id")
        mine = _with_counts(Plan.objects.filter(Q(host=profile) | Q(pk__in=going))).order_by("-starts_at")[:10]
        going_ids = set(PlanRSVP.objects.filter(profile=profile).values_list("plan_id", flat=True))
    else:
        going_ids = set()
    return render(request, "connect/plan_list.html", {
        "profile": profile, "upcoming": upcoming, "mine": mine, "going_ids": going_ids, "now": timezone.now(),
    })


def plan_create(request):
    profile = _profile(request)
    if profile is None:  # a page, not a redirect, as on /meet/: it says why a profile comes first
        return render(request, "connect/plan_form.html", {"form": None})
    form = PlanForm(request.POST or None)
    if form.is_valid():
        plan = form.save(commit=False)
        plan.host = profile
        plan.save()
        messages.success(request, "Your plan is posted. Anyone signed in can see it and join.")
        return redirect(plan)
    return render(request, "connect/plan_form.html", {"form": form})


def plan_detail(request, pk):
    plan = get_object_or_404(Plan.objects.select_related("host", "location"), pk=pk)
    profile = _profile(request)
    return render(request, "connect/plan_detail.html", {
        "plan": plan,
        "profile": profile,
        "rsvps": plan.rsvps.select_related("profile"),
        **state(plan, profile),
    })


@require_POST
def plan_rsvp(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    profile = _profile(request)
    if profile is None:
        messages.info(request, "Set up your profile first, so the host knows who's coming.")
        return redirect("connect:profile")
    now = state(plan, profile)
    action = request.POST.get("action")
    if action == "join" and now["can_join"]:
        try:
            join(plan, profile)
            messages.success(request, "You're going. See you there!")
        except Full:
            messages.info(request, "Someone took the last place just before you. This plan is full.")
        except IntegrityError:  # a second click: the first one counted
            pass
    elif action == "leave" and now["can_leave"]:
        plan.rsvps.filter(profile=profile).delete()
        messages.info(request, "You're no longer going. Your place is free for someone else.")
    else:  # a page left open too long, or a second click
        messages.info(request, "That can't be done any more. Here is where things stand.")
    return redirect(plan)


@require_POST
def plan_cancel(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if state(plan, _profile(request))["can_cancel"]:
        plan.cancelled_at = timezone.now()
        plan.save(update_fields=["cancelled_at"])
        messages.info(request, "Your plan is called off. Everyone going will see that on its page.")
    else:
        messages.info(request, "That can't be done any more. Here is where things stand.")
    return redirect(plan)
