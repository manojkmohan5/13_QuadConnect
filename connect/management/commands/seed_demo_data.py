"""
Seed realistic test data for the QuadConnect data model.

Run with:  python manage.py seed_demo_data

Creates eight verified student profiles, a shared interest catalogue, weekend
availability, four approved campus locations, and three weekly matches (one
Friend Connect, one Squad Connect, one completed experience with feedback) so
that every relationship in the model is populated and inspectable in Admin.

Idempotent: re-running updates the same rows instead of duplicating them.
"""

from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from connect.models import (
    AvailabilitySlot,
    CampusLocation,
    ConnectionType,
    ConversationStyle,
    ExperienceFeedback,
    GroupPreference,
    Interest,
    InterestCategory,
    Match,
    MatchParticipant,
    MatchStatus,
    ParticipantResponse,
    ProfileInterest,
    SocialEnergy,
    StudentProfile,
    TimeBlock,
    Weekday,
)

# --- Catalogue -------------------------------------------------------------

HOBBIES = [
    "Basketball", "Gaming", "Music", "Movies", "Food", "Fitness", "Art",
    "Travel", "Reading", "Technology", "Outdoors", "Photography",
]
RSOS = [
    "Illinois Student Government", "Engineers Without Borders",
    "UIUC Dance Marathon", "Business Illini", "Illini Media", "UIUC Esports",
    "Habitat for Humanity UIUC", "Indian Students Association",
    "UIUC Pre-Med Society", "Illini Robotics",
]
ACTIVITIES = [
    "Coffee", "Campus walk", "Food", "Board games", "Sports",
    "Study/social space",
]

LOCATIONS = [
    ("Illini Union", "1401 W Green St, Urbana", "Main entrance, ground floor lobby", True, 12),
    ("Grainger Engineering Library", "1301 W Springfield Ave, Urbana", "First floor commons", True, 8),
    ("The Main Quad", "601 S Wright St, Champaign", "South end, by the Alma Mater", False, 20),
    ("Espresso Royale on Goodwin", "1117 W Oregon St, Urbana", "Counter seating area", True, 6),
]

# net_id, name, college, department, job, connection, energy, style, group,
# same_age, shared_rso, cross_dept
STUDENTS = [
    ("jordan4", "Jordan Alvarez", "Grainger College of Engineering",
     "Computer Science", "Campus Dining - Server", ConnectionType.FRIEND,
     SocialEnergy.BALANCED, ConversationStyle.CASUAL, GroupPreference.EITHER,
     True, True, True),
    ("apatel22", "Aditi Patel", "Gies College of Business",
     "Finance + Statistics", "", ConnectionType.SQUAD,
     SocialEnergy.VERY_SOCIAL, ConversationStyle.ACTIVITY,
     GroupPreference.SMALL, True, False, True),
    ("mchen9", "Ming Chen", "Grainger College of Engineering",
     "Mechanical Engineering", "Grainger IT Help Desk", ConnectionType.SQUAD,
     SocialEnergy.RESERVED, ConversationStyle.DEEP, GroupPreference.SMALL,
     False, True, False),
    ("skoval3", "Sofia Kovalenko", "College of Liberal Arts & Sciences",
     "Psychology", "", ConnectionType.FRIEND,
     SocialEnergy.QUIET, ConversationStyle.DEEP, GroupPreference.ONE,
     True, False, True),
    ("dokafor2", "Daniel Okafor", "College of Media",
     "Journalism", "Illini Media - Staff Writer", ConnectionType.SQUAD,
     SocialEnergy.OUTGOING, ConversationStyle.CASUAL, GroupPreference.SMALL,
     True, True, True),
    ("rlin7", "Rachel Lin", "Grainger College of Engineering",
     "Bioengineering", "", ConnectionType.SQUAD,
     SocialEnergy.BALANCED, ConversationStyle.ACTIVITY,
     GroupPreference.SMALL, True, True, False),
    ("tbrooks5", "Tyler Brooks", "College of Applied Health Sciences",
     "Kinesiology", "ARC - Intramural Referee", ConnectionType.SQUAD,
     SocialEnergy.OUTGOING, ConversationStyle.ACTIVITY,
     GroupPreference.SMALL, True, False, True),
    ("nhaddad4", "Nour Haddad", "College of Fine & Applied Arts",
     "Graphic Design", "", ConnectionType.FRIEND,
     SocialEnergy.RESERVED, ConversationStyle.CASUAL, GroupPreference.ONE,
     False, False, True),
]

# net_id -> (hobby picks, rso picks, starred hobbies)
PICKS = {
    "jordan4":  (["Basketball", "Gaming", "Food", "Music"], ["UIUC Esports"], ["Basketball", "Gaming"]),
    "apatel22": (["Food", "Travel", "Fitness", "Music"], ["Business Illini", "UIUC Dance Marathon"], ["Food"]),
    "mchen9":   (["Gaming", "Technology", "Movies"], ["Illini Robotics", "UIUC Esports"], ["Technology"]),
    "skoval3":  (["Reading", "Art", "Movies"], ["UIUC Pre-Med Society"], ["Reading"]),
    "dokafor2": (["Music", "Movies", "Food", "Photography"], ["Illini Media", "Illinois Student Government"], ["Music"]),
    "rlin7":    (["Fitness", "Outdoors", "Food", "Gaming"], ["Habitat for Humanity UIUC", "UIUC Esports"], ["Outdoors"]),
    "tbrooks5": (["Basketball", "Fitness", "Outdoors"], ["Engineers Without Borders"], ["Basketball", "Fitness"]),
    "nhaddad4": (["Art", "Photography", "Reading", "Movies"], ["Indian Students Association"], ["Art"]),
}

# net_id -> [(weekday, time_block), ...]
AVAILABILITY = {
    "jordan4":  [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SUNDAY, TimeBlock.MIDDAY)],
    "apatel22": [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SATURDAY, TimeBlock.EVENING)],
    "mchen9":   [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SUNDAY, TimeBlock.MORNING)],
    "skoval3":  [(Weekday.SUNDAY, TimeBlock.MIDDAY), (Weekday.SUNDAY, TimeBlock.AFTERNOON)],
    "dokafor2": [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SUNDAY, TimeBlock.EVENING)],
    "rlin7":    [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SATURDAY, TimeBlock.MORNING)],
    "tbrooks5": [(Weekday.SATURDAY, TimeBlock.AFTERNOON), (Weekday.SUNDAY, TimeBlock.AFTERNOON)],
    "nhaddad4": [(Weekday.SUNDAY, TimeBlock.MIDDAY), (Weekday.SATURDAY, TimeBlock.MORNING)],
}


class Command(BaseCommand):
    help = "Seed realistic QuadConnect test data (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        interests = self._seed_interests()
        locations = self._seed_locations()
        profiles = self._seed_profiles()
        self._seed_picks(profiles, interests)
        self._seed_availability(profiles)
        self._seed_matches(profiles, interests, locations)
        self._summarise()

    # -- catalogue ------------------------------------------------------
    def _seed_interests(self):
        catalogue = {}
        for names, category in (
            (HOBBIES, InterestCategory.HOBBY),
            (RSOS, InterestCategory.RSO),
            (ACTIVITIES, InterestCategory.ACTIVITY),
        ):
            for name in names:
                obj, _ = Interest.objects.get_or_create(
                    name=name, category=category
                )
                catalogue[(name, category)] = obj
        self.stdout.write(f"Interests in catalogue: {Interest.objects.count()}")
        return catalogue

    def _seed_locations(self):
        out = {}
        for name, addr, note, indoor, cap in LOCATIONS:
            obj, _ = CampusLocation.objects.update_or_create(
                name=name,
                defaults={
                    "street_address": addr,
                    "arrival_note": note,
                    "is_indoor": indoor,
                    "capacity": cap,
                },
            )
            out[name] = obj
        self.stdout.write(f"Approved campus locations: {len(out)}")
        return out

    # -- students -------------------------------------------------------
    def _seed_profiles(self):
        profiles = {}
        for (net_id, full_name, college, dept, job, conn, energy, style,
             group, same_age, shared_rso, cross_dept) in STUDENTS:
            user, created = User.objects.get_or_create(
                username=net_id,
                defaults={
                    "email": f"{net_id}@illinois.edu",
                    "first_name": full_name.split()[0],
                    "last_name": full_name.split()[-1],
                },
            )
            if created:
                user.set_unusable_password()  # real auth arrives via SSO
                user.save()
            profile, _ = StudentProfile.objects.update_or_create(
                net_id=net_id,
                defaults={
                    "user": user,
                    "illinois_email": f"{net_id}@illinois.edu",
                    "full_name": full_name,
                    "college": college,
                    "department": dept,
                    "part_time_job": job,
                    "preferred_connection": conn,
                    "social_energy": energy,
                    "conversation_style": style,
                    "group_preference": group,
                    "prefers_same_age": same_age,
                    "prefers_shared_rso": shared_rso,
                    "open_to_other_departments": cross_dept,
                    "is_sso_verified": True,
                    "onboarding_completed_at": timezone.now(),
                },
            )
            profiles[net_id] = profile
        self.stdout.write(f"Student profiles: {len(profiles)}")
        return profiles

    def _seed_picks(self, profiles, interests):
        n = 0
        for net_id, (hobbies, rsos, starred) in PICKS.items():
            profile = profiles[net_id]
            for name in hobbies:
                ProfileInterest.objects.update_or_create(
                    profile=profile,
                    interest=interests[(name, InterestCategory.HOBBY)],
                    defaults={"is_primary": name in starred},
                )
                n += 1
            for name in rsos:
                ProfileInterest.objects.update_or_create(
                    profile=profile,
                    interest=interests[(name, InterestCategory.RSO)],
                    defaults={"is_primary": False},
                )
                n += 1
        self.stdout.write(f"Interest selections (M2M through-rows): {n}")

    def _seed_availability(self, profiles):
        n = 0
        for net_id, slots in AVAILABILITY.items():
            for weekday, block in slots:
                AvailabilitySlot.objects.get_or_create(
                    profile=profiles[net_id], weekday=weekday, time_block=block
                )
                n += 1
        self.stdout.write(f"Availability slots: {n}")

    # -- matches --------------------------------------------------------
    def _seed_matches(self, profiles, interests, locations):
        tz = timezone.get_current_timezone()
        this_monday = date(2026, 9, 7)
        last_monday = this_monday - timedelta(days=7)

        def aware(d, t):
            return timezone.make_aware(datetime.combine(d, t), tz)

        coffee = interests[("Coffee", InterestCategory.ACTIVITY)]
        games = interests[("Board games", InterestCategory.ACTIVITY)]
        walk = interests[("Campus walk", InterestCategory.ACTIVITY)]

        # 1) Friend Connect, current week, awaiting responses (Screen 6)
        friend, _ = Match.objects.update_or_create(
            check_in_code="QC-4827",
            defaults={
                "connection_type": ConnectionType.FRIEND,
                "week_start": this_monday,
                "scheduled_for": aware(date(2026, 9, 12), time(14, 0)),
                "location": locations["Espresso Royale on Goodwin"],
                "suggested_activity": coffee,
                "status": MatchStatus.PROPOSED,
            },
        )
        self._participants(friend, [
            ("jordan4", ParticipantResponse.ACCEPTED, 91.50,
             "Basketball, Gaming, Coffee, Saturday availability"),
            ("nhaddad4", ParticipantResponse.PENDING, 88.25,
             "Art, Movies, quiet conversation style"),
        ], profiles)

        # 2) Squad Connect, current week, confirmed (Screens 7 and 8)
        squad, _ = Match.objects.update_or_create(
            check_in_code="QC-5193",
            defaults={
                "connection_type": ConnectionType.SQUAD,
                "week_start": this_monday,
                "scheduled_for": aware(date(2026, 9, 12), time(14, 0)),
                "location": locations["Illini Union"],
                "suggested_activity": games,
                "status": MatchStatus.CONFIRMED,
            },
        )
        checked_in = aware(date(2026, 9, 12), time(13, 52))
        self._participants(squad, [
            ("apatel22", ParticipantResponse.ACCEPTED, 87.00, "Food, Music, Fitness", checked_in),
            ("mchen9", ParticipantResponse.ACCEPTED, 84.75, "Gaming, UIUC Esports, Movies", checked_in),
            ("dokafor2", ParticipantResponse.ACCEPTED, 82.40, "Music, Movies, Food"),
            ("rlin7", ParticipantResponse.ACCEPTED, 80.10, "Gaming, Food, UIUC Esports"),
            ("tbrooks5", ParticipantResponse.PENDING, 76.80, "Fitness, Outdoors, Basketball"),
        ], profiles)

        # 3) Completed Friend Connect from last week, with feedback (Screen 9)
        done, _ = Match.objects.update_or_create(
            check_in_code="QC-3312",
            defaults={
                "connection_type": ConnectionType.FRIEND,
                "week_start": last_monday,
                "scheduled_for": aware(date(2026, 9, 6), time(12, 0)),
                "location": locations["The Main Quad"],
                "suggested_activity": walk,
                "status": MatchStatus.COMPLETED,
            },
        )
        done_ci = aware(date(2026, 9, 6), time(11, 58))
        self._participants(done, [
            ("skoval3", ParticipantResponse.ACCEPTED, 93.20, "Reading, Art, Movies, Sunday availability", done_ci),
            ("mchen9", ParticipantResponse.ACCEPTED, 93.20, "Movies, deep conversation style", done_ci),
        ], profiles)

        for net_id, rating, connect, note in (
            ("skoval3", 5, True, "Easy conversation, would meet again."),
            ("mchen9", 4, True, "Good walk. Slightly short on time."),
        ):
            participant = MatchParticipant.objects.get(
                match=done, profile=profiles[net_id]
            )
            ExperienceFeedback.objects.update_or_create(
                participant=participant,
                defaults={
                    "rating": rating,
                    "enjoyed_conversation": True,
                    "enjoyed_shared_interests": True,
                    "enjoyed_activity": rating == 5,
                    "felt_comfortable": True,
                    "wants_to_stay_connected": connect,
                    "private_note": note,
                },
            )
        self.stdout.write(
            f"Matches: {Match.objects.count()} | "
            f"participants: {MatchParticipant.objects.count()} | "
            f"feedback: {ExperienceFeedback.objects.count()}"
        )

    def _participants(self, match, rows, profiles):
        for row in rows:
            net_id, response, score, reason = row[:4]
            checked_in = row[4] if len(row) > 4 else None
            MatchParticipant.objects.update_or_create(
                match=match,
                profile=profiles[net_id],
                defaults={
                    "response": response,
                    "compatibility_score": score,
                    "match_reason": reason,
                    "checked_in_at": checked_in,
                },
            )

    def _summarise(self):
        self.stdout.write(self.style.SUCCESS("\nSeed complete."))
        for model in (StudentProfile, Interest, ProfileInterest,
                      AvailabilitySlot, CampusLocation, Match,
                      MatchParticipant, ExperienceFeedback):
            self.stdout.write(
                f"  {model._meta.verbose_name:24s} {model.objects.count():>4} rows"
            )
