"""
Weekend matching: who meets whom, when and where, and what happens after.

A student signs up for the coming weekend (a MatchRequest), one-on-one
(Friend Connect) or in a group (Squad Connect). Every sign-up, decline and
withdrawal runs match_week() for that weekend at once, so a student is
matched as soon as someone suitable is in the pool:

  Friend Connect  the two waiting students who share the most interests (a
                  starred interest counts double) and are both free at one
                  of the weekend's blocks still ahead.
  Squad Connect   4 to 8 waiting students free at the same block who picked
                  the same interest, the biggest such group first.

Two students who were in a match together that weekend, whatever became of
it, are never put together again that weekend.

The meetup is the soonest block they share, at an approved venue that seats
them all, with a check-in code and an activity that suits what they share. Then, for each student in it:

  respond()   accept or decline, until the meetup starts. Everyone left has
              accepted: CONFIRMED. Too few left (under 2 in a 1-on-1, under
              3 in a squad): CANCELLED, and the rest are matched again.
  check_in()  for a student who accepted, from 30 minutes before the start
              to the end of the block. Two check-ins: COMPLETED, they met.
  feedback    (connect/meetups.py) once checked in. Students who both want
              to stay connected see each other's Illinois address.
"""

import secrets
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from itertools import combinations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    CampusLocation,
    ConnectionType,
    Interest,
    InterestCategory,
    Match,
    MatchParticipant,
    MatchRequest,
    MatchStatus,
    ParticipantResponse,
    StudentProfile,
    TimeBlock,
    Weekday,
)

SQUAD_SIZE = (4, 8)  # as ConnectionType.SQUAD says: "4-8 students"
STILL_ON = {ConnectionType.FRIEND: 2, ConnectionType.SQUAD: 3}  # fewer left: called off
LEAD = timedelta(hours=2)  # a meetup is never closer than this when it is made
CHECK_IN_OPENS = timedelta(minutes=30)  # before the start
BLOCK = timedelta(hours=2)  # every TimeBlock is two hours long
GOING_AHEAD = [MatchStatus.PROPOSED, MatchStatus.CONFIRMED, MatchStatus.COMPLETED]
# What to do, from an interest everyone in the match picked: a meeting
# activity in the catalogue (InterestCategory.ACTIVITY). Coffee otherwise.
ACTIVITIES = {
    "Basketball": "Sports", "Fitness": "Sports", "Gym": "Sports",
    "Gaming": "Board games", "UIUC Esports": "Board games", "Food": "Food",
    "Outdoors": "Campus walk", "Photography": "Campus walk", "Travel": "Campus walk",
    "Reading": "Study/social space", "Technology": "Study/social space",
}

# ponytail: one lock for the process, so two sign-ups at the same moment
# cannot put one student in two matches. More than one server process would
# need a database lock instead.
_lock = threading.RLock()


@dataclass(frozen=True)
class Slot:
    """One weekend block, and when it starts."""
    day: int  # Weekday
    block: str  # TimeBlock
    start: datetime


@dataclass
class Waiting:
    """A signed-up student in no match yet, as matching sees them."""
    profile: StudentProfile
    kind: str  # ConnectionType
    weights: dict  # interest id -> 2 if starred, else 1
    names: dict  # interest id -> name
    free: set  # {(weekday, block)}


def weekend_slots(week_start, now=None):
    """That weekend's blocks that start at least LEAD from now, soonest first."""
    now = now or timezone.now()
    slots = []
    for day in Weekday:
        date = week_start + timedelta(days=day - 1)  # ISO weekdays: Monday is 1
        for block in TimeBlock:
            start = timezone.make_aware(datetime.combine(date, time(int(block.value.split("-")[0]))))
            if start >= now + LEAD:
                slots.append(Slot(day, block, start))
    return slots


def coming_week(now=None):
    """The Monday of the weekend to sign up for: this week's, until its last
    block is too close, then next week's."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    monday = today - timedelta(days=today.weekday())
    return monday if weekend_slots(monday, now) else monday + timedelta(days=7)


def current_match(profile, week_start):
    """The student's place in a match going ahead that weekend, if any."""
    return (MatchParticipant.objects
            .filter(profile=profile, match__week_start=week_start, match__status__in=GOING_AHEAD)
            .exclude(response=ParticipantResponse.DECLINED)
            .select_related("match", "match__location").first())


def sign_up(profile, kind, week_start, now=None):
    """Sign the student up for the weekend, and match whoever can be matched now."""
    MatchRequest.objects.get_or_create(profile=profile, week_start=week_start,
                                       defaults={"connection_type": kind})
    return match_week(week_start, now)


def leave(profile, week_start, now=None):
    """Withdraw from the weekend: decline the match going ahead, while that
    is still possible, and give up the sign-up. The others are matched again."""
    with _lock, transaction.atomic():
        current = current_match(profile, week_start)
        if current and can_answer(current, now):
            current.response = ParticipantResponse.DECLINED
            current.save(update_fields=["response"])
            settle(current.match)
        MatchRequest.objects.filter(profile=profile, week_start=week_start).delete()
    match_week(week_start, now)


def match_week(week_start, now=None):
    """Match everyone waiting for that weekend who can be. Returns the new matches."""
    slots = weekend_slots(week_start, now)
    with _lock, transaction.atomic():
        waiting = _waiting(week_start)
        new = _pair([w for w in waiting if w.kind == ConnectionType.FRIEND], week_start, slots)
        return new + _group([w for w in waiting if w.kind == ConnectionType.SQUAD], week_start, slots)


def _waiting(week_start):
    """Everyone signed up for the weekend who is in no match going ahead,
    in the order they signed up. A student who declined a match is back."""
    busy = (MatchParticipant.objects
            .filter(match__week_start=week_start, match__status__in=GOING_AHEAD)
            .exclude(response=ParticipantResponse.DECLINED).values("profile"))
    signups = (MatchRequest.objects.filter(week_start=week_start).exclude(profile__in=busy)
               .select_related("profile").order_by("created_at", "pk")
               .prefetch_related("profile__interest_links__interest", "profile__availability_slots"))
    waiting = []
    for signup in signups:
        links = signup.profile.interest_links.all()
        waiting.append(Waiting(
            signup.profile, signup.connection_type,
            {link.interest_id: 2 if link.is_primary else 1 for link in links},
            {link.interest_id: link.interest.name for link in links},
            {(slot.weekday, slot.time_block) for slot in signup.profile.availability_slots.all()},
        ))
    return waiting


def _pair(friends, week_start, slots):
    """1-on-1s: the best-matched pairs first, each student in one."""
    met = _met(week_start)
    options = []
    # ponytail: every pair, O(n²); split the pool by block first if a
    # weekend's sign-ups ever reach the thousands.
    for i, j in combinations(range(len(friends)), 2):
        a, b = friends[i], friends[j]
        shared = a.weights.keys() & b.weights.keys()
        free = [s for s in slots if (s.day, s.block) in a.free and (s.day, s.block) in b.free]
        if shared and free and frozenset((a.profile.pk, b.profile.pk)) not in met:
            score = sum(a.weights[k] + b.weights[k] for k in shared)
            options.append((-score, free[0].start, i, j, free[0]))  # best, soonest, first to sign up
    paired, new = set(), []
    for _score, _start, i, j, slot in sorted(options):
        if paired.isdisjoint((i, j)):
            match = _create(ConnectionType.FRIEND, [friends[i], friends[j]], week_start, slot)
            if match:
                paired |= {i, j}
                new.append(match)
    return new


def _met(week_start):
    """Every pair of students who were in a match together that weekend."""
    members = defaultdict(set)
    for match, profile in (MatchParticipant.objects.filter(match__week_start=week_start)
                           .values_list("match", "profile")):
        members[match].add(profile)
    return {frozenset(pair) for group in members.values() for pair in combinations(group, 2)}


def _group(squad, week_start, slots):
    """Squads: at each block, the students free then who picked one same
    interest; the biggest group first, up to 8, earliest sign-ups first."""
    smallest, largest = SQUAD_SIZE
    met = _met(week_start)
    left, new = list(range(len(squad))), []
    while True:
        best = None
        for slot in slots:
            by_interest = defaultdict(list)
            for i in left:
                if (slot.day, slot.block) in squad[i].free:
                    for interest in squad[i].weights:
                        by_interest[interest].append(i)
            for interest in sorted(by_interest):
                members = []
                for i in by_interest[interest]:  # in sign-up order, nobody they have met
                    if len(members) < largest and all(
                            frozenset((squad[i].profile.pk, squad[j].profile.pk)) not in met for j in members):
                        members.append(i)
                if len(members) >= smallest and (best is None or len(members) > len(best[1])):
                    best = (slot, members)
        if best is None:
            return new
        slot, members = best
        match = _create(ConnectionType.SQUAD, [squad[i] for i in members], week_start, slot)
        if match is None:  # no approved venue seats them all
            return new
        new.append(match)
        left = [i for i in left if i not in members]


def _create(kind, members, week_start, slot):
    """The match: at the approved venue that seats everyone and has the
    fewest meetups at that time. None if no venue is big enough. Each
    member's reason is the interests they share with the others."""
    venue = (CampusLocation.objects.filter(is_approved=True, capacity__gte=len(members))
             .annotate(booked=Count("matches", filter=Q(matches__scheduled_for=slot.start)))
             .order_by("booked", "capacity", "name").first())
    if venue is None:
        return None
    match = Match.objects.create(connection_type=kind, week_start=week_start, scheduled_for=slot.start,
                                 location=venue, check_in_code=_new_code(), suggested_activity=_activity(members))
    for member in members:
        others = set().union(*(m.weights.keys() for m in members if m is not member))
        shared = sorted(member.weights.keys() & others, key=lambda k: (-member.weights[k], member.names[k]))
        MatchParticipant.objects.create(
            match=match, profile=member.profile,
            compatibility_score=round(100 * len(shared) / max(len(member.weights), 1)),
            match_reason=", ".join(member.names[k] for k in shared)[:250])
    return match


def _activity(members):
    """The meeting activity for an interest they all picked, or Coffee;
    None if the catalogue has no such activity."""
    common = set.intersection(*(set(m.weights) for m in members))
    names = sorted(members[0].names[k] for k in common)
    wanted = next((ACTIVITIES[name] for name in names if name in ACTIVITIES), "Coffee")
    return Interest.objects.filter(category=InterestCategory.ACTIVITY, name=wanted, is_active=True).first()


def _new_code():
    """An unused check-in code: QC- and four digits (Screen 8)."""
    while True:  # ponytail: 9,000 codes in all; make them longer well before they run out
        code = f"QC-{secrets.randbelow(9000) + 1000}"
        if not Match.objects.filter(check_in_code=code).exists():
            return code


def settle(match):
    """Bring the match's status up to date with its members' answers and check-ins."""
    match.refresh_from_db(fields=["status"])  # another request may have changed it
    if match.status in (MatchStatus.CANCELLED, MatchStatus.COMPLETED):
        return
    left = match.participants.exclude(response=ParticipantResponse.DECLINED)
    if left.count() < STILL_ON[match.connection_type]:
        match.status = MatchStatus.CANCELLED
    elif left.filter(checked_in_at__isnull=False).count() >= 2:
        match.status = MatchStatus.COMPLETED
    elif not left.exclude(response=ParticipantResponse.ACCEPTED).exists():
        match.status = MatchStatus.CONFIRMED
    else:
        match.status = MatchStatus.PROPOSED
    match.save(update_fields=["status"])


def can_answer(participant, now=None):
    """Accept or decline: until the meetup starts, while it is going ahead."""
    now = now or timezone.now()
    match = participant.match
    return (match.status in (MatchStatus.PROPOSED, MatchStatus.CONFIRMED)
            and participant.response != ParticipantResponse.DECLINED
            and now < match.scheduled_for)


def respond(participant, accept, now=None):
    """Accept or decline. A decline that calls the match off puts the others
    back in the pool, and the decliner is in it too, for someone else."""
    with _lock, transaction.atomic():
        participant.response = ParticipantResponse.ACCEPTED if accept else ParticipantResponse.DECLINED
        participant.save(update_fields=["response"])
        settle(participant.match)
    if not accept:
        match_week(participant.match.week_start, now)


def can_check_in(participant, now=None):
    """For a student who accepted a match going ahead, from 30 minutes
    before the start to the end of its block."""
    now = now or timezone.now()
    match = participant.match
    return (match.status in GOING_AHEAD
            and participant.response == ParticipantResponse.ACCEPTED
            and participant.checked_in_at is None
            and match.scheduled_for - CHECK_IN_OPENS <= now <= match.scheduled_for + BLOCK)


def check_in(participant, now=None):
    """Record that the student is at the meetup. The second check-in completes it."""
    with _lock, transaction.atomic():
        participant.checked_in_at = now or timezone.now()
        participant.save(update_fields=["checked_in_at"])
        settle(participant.match)


def can_give_feedback(participant):
    """Once, after checking in."""
    return participant.checked_in_at is not None and getattr(participant, "feedback", None) is None


def stay_connected(participant):
    """When this student asked to stay connected: the others in the match who
    asked too. Each side then sees the other's Illinois address."""
    mine = getattr(participant, "feedback", None)
    if not (mine and mine.wants_to_stay_connected):
        return []
    return [p.profile for p in participant.match.participants.select_related("profile")
            .exclude(pk=participant.pk).filter(feedback__wants_to_stay_connected=True)]
