"""
Seed realistic test data for the QuadConnect data model.

Run with:  python manage.py seed_demo_data

Creates thirty-eight verified student profiles (the eight of the summer
pilot, and thirty fall sign-ups who have no match yet), a shared interest
catalogue, weekend availability, four approved campus locations, and nineteen
weekly matches
over nine weeks: a summer pilot from mid-July, the first fall weeks, and the
current week's two matches (one proposed, one confirmed). Completed matches
carry check-ins and private feedback, so every relationship in the model is
populated and inspectable in Admin. It also creates the two course staff
accounts the assignments ask for.

Idempotent and deterministic: re-running updates the same rows with the
same values instead of duplicating them, so the committed db.sqlite3 can be
rebuilt exactly.
"""

from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
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
# Hobbies added after the first catalogue. They are created last, so the
# interests above keep their ids in a database seeded before they existed.
LATER_HOBBIES = ["Gym"]

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

# When each student finished onboarding: fixed dates before the first
# match, so a re-seed reproduces the same rows.
ONBOARDED = {
    "jordan4": date(2026, 6, 29), "nhaddad4": date(2026, 6, 30),
    "apatel22": date(2026, 7, 1), "dokafor2": date(2026, 7, 2),
    "rlin7": date(2026, 7, 6), "tbrooks5": date(2026, 7, 7),
    "skoval3": date(2026, 7, 8), "mchen9": date(2026, 7, 9),
}

# Past weekly cycles, oldest first: a summer pilot from mid-July, then the
# first fall weeks. Each row is (week start, check-in code, type, day,
# start time, venue, suggested activity, status, participants, ratings).
# Every student appears at most once per week, as the matching rules
# require. Ratings become private feedback rows.
SAT, SUN = 5, 6
F, S = ConnectionType.FRIEND, ConnectionType.SQUAD
DONE, CANCELLED = MatchStatus.COMPLETED, MatchStatus.CANCELLED
HISTORY = [
    (date(2026, 7, 13), "QC-1301", F, SUN, time(12), "Espresso Royale on Goodwin", "Coffee", DONE,
     ["jordan4", "nhaddad4"], {"jordan4": 4, "nhaddad4": 4}),
    (date(2026, 7, 20), "QC-1302", S, SAT, time(14), "Illini Union", "Board games", DONE,
     ["apatel22", "dokafor2", "rlin7", "tbrooks5"],
     {"apatel22": 5, "dokafor2": 4, "rlin7": 4, "tbrooks5": 3}),
    (date(2026, 7, 27), "QC-1303", F, SUN, time(12), "Grainger Engineering Library", "Study/social space", DONE,
     ["skoval3", "nhaddad4"], {"skoval3": 5, "nhaddad4": 5}),
    (date(2026, 7, 27), "QC-1304", S, SAT, time(14), "The Main Quad", "Sports", DONE,
     ["apatel22", "mchen9", "rlin7", "tbrooks5"], {"tbrooks5": 5, "rlin7": 4}),
    (date(2026, 8, 3), "QC-1305", F, SUN, time(12), "Espresso Royale on Goodwin", "Coffee", DONE,
     ["jordan4", "skoval3"], {"jordan4": 3, "skoval3": 3}),
    (date(2026, 8, 3), "QC-1306", S, SAT, time(14), "Illini Union", "Board games", CANCELLED,
     ["apatel22", "dokafor2", "mchen9", "rlin7"], {}),
    (date(2026, 8, 10), "QC-1307", F, SAT, time(14), "Grainger Engineering Library", "Board games", DONE,
     ["jordan4", "mchen9"], {"jordan4": 5, "mchen9": 4}),
    (date(2026, 8, 10), "QC-1308", S, SAT, time(14), "The Main Quad", "Campus walk", DONE,
     ["apatel22", "dokafor2", "rlin7", "tbrooks5"], {"dokafor2": 4, "apatel22": 4}),
    (date(2026, 8, 17), "QC-1309", F, SUN, time(12), "Espresso Royale on Goodwin", "Coffee", DONE,
     ["skoval3", "nhaddad4"], {"skoval3": 5, "nhaddad4": 4}),
    (date(2026, 8, 17), "QC-1310", F, SAT, time(14), "Illini Union", "Food", DONE,
     ["jordan4", "rlin7"], {"rlin7": 4}),
    (date(2026, 8, 17), "QC-1311", S, SAT, time(14), "Grainger Engineering Library", "Board games", DONE,
     ["apatel22", "mchen9", "dokafor2", "tbrooks5"], {"mchen9": 4, "tbrooks5": 4, "apatel22": 5}),
    (date(2026, 8, 24), "QC-1312", F, SUN, time(12), "Espresso Royale on Goodwin", "Coffee", DONE,
     ["jordan4", "nhaddad4"], {"jordan4": 5, "nhaddad4": 4}),
    (date(2026, 8, 24), "QC-1313", S, SAT, time(14), "Illini Union", "Sports", DONE,
     ["apatel22", "dokafor2", "tbrooks5", "rlin7"], {"apatel22": 4, "tbrooks5": 5}),
    (date(2026, 8, 24), "QC-1314", F, SUN, time(12), "Grainger Engineering Library", "Study/social space", DONE,
     ["skoval3", "mchen9"], {"skoval3": 5, "mchen9": 4}),
    (date(2026, 8, 31), "QC-1315", S, SAT, time(14), "The Main Quad", "Sports", DONE,
     ["apatel22", "dokafor2", "rlin7", "tbrooks5"], {"dokafor2": 5, "rlin7": 4}),
    (date(2026, 8, 31), "QC-1316", F, SUN, time(12), "Espresso Royale on Goodwin", "Coffee", DONE,
     ["jordan4", "nhaddad4"], {"jordan4": 4}),
]
# Who said no to the one cancelled match.
DECLINED = {"QC-1306": {"dokafor2", "mchen9"}}

# The fall sign-ups: thirty more students, in none of the matches above, so a
# search has more students to find. One row each, in the order of STUDENTS,
# then their hobbies, student organisations, starred hobbies and free slots.
ENG, BUS, LAS = ("Grainger College of Engineering", "Gies College of Business",
                 "College of Liberal Arts & Sciences")
MEDIA, AHS, FAA = ("College of Media", "College of Applied Health Sciences",
                   "College of Fine & Applied Arts")
QUIET, RESERVED, BALANCED, OUTGOING, VERY_SOCIAL = SocialEnergy  # 1 to 5
CASUAL, DEEP, ACTIVITY = ConversationStyle.CASUAL, ConversationStyle.DEEP, ConversationStyle.ACTIVITY
ONE, SMALL, EITHER = GroupPreference.ONE, GroupPreference.SMALL, GroupPreference.EITHER
SA, SU = Weekday.SATURDAY, Weekday.SUNDAY
MORNING, MIDDAY, AFTERNOON, EVENING = TimeBlock.MORNING, TimeBlock.MIDDAY, TimeBlock.AFTERNOON, TimeBlock.EVENING
FALL_STUDENTS = [
    ("mgarcia8", "Maya Garcia", ENG, "Computer Engineering", "", S, BALANCED, ACTIVITY, SMALL, True, True, True,
     ["Gaming", "Technology", "Gym"], ["UIUC Esports", "Illini Robotics"], ["Gaming"], [(SA, AFTERNOON), (SA, EVENING)]),
    ("ekim21", "Ethan Kim", ENG, "Electrical Engineering", "ECE Lab Assistant", F, QUIET, DEEP, ONE, True, False, False,
     ["Reading", "Technology", "Gaming"], ["Illini Robotics"], ["Reading"], [(SU, MIDDAY), (SA, AFTERNOON)]),
    ("lrossi4", "Lucia Rossi", FAA, "Studio Art", "Krannert Art Museum - Gallery Attendant", F, RESERVED, DEEP, ONE,
     False, False, True, ["Art", "Photography", "Travel"], ["Habitat for Humanity UIUC"], ["Art"],
     [(SU, AFTERNOON), (SU, MIDDAY)]),
    ("jwash7", "Jamal Washington", AHS, "Kinesiology", "ARC - Fitness Desk", S, OUTGOING, ACTIVITY, SMALL, True, False,
     True, ["Gym", "Basketball", "Fitness", "Music"], [], ["Gym", "Basketball"], [(SA, MORNING), (SA, AFTERNOON)]),
    ("hsato2", "Hana Sato", LAS, "Linguistics", "", F, QUIET, DEEP, ONE, True, False, True,
     ["Reading", "Movies", "Music"], [], ["Reading"], [(SU, MORNING), (SU, MIDDAY)]),
    ("tadeyem2", "Tobi Adeyemi", BUS, "Accountancy", "Gies Career Services - Peer Advisor", S, VERY_SOCIAL, CASUAL,
     SMALL, True, True, True, ["Food", "Travel", "Music", "Basketball"], ["Business Illini"], ["Food"],
     [(SA, EVENING), (SU, AFTERNOON)]),
    ("cmorale5", "Carlos Morales", ENG, "Civil Engineering", "", S, BALANCED, ACTIVITY, EITHER, False, True, True,
     ["Outdoors", "Photography", "Gym"], ["Engineers Without Borders"], ["Outdoors"], [(SA, MORNING), (SU, AFTERNOON)]),
    ("akhan14", "Ayesha Khan", AHS, "Community Health", "McKinley Health Center - Front Desk", F, BALANCED, CASUAL, ONE,
     True, False, True, ["Fitness", "Gym", "Food"], ["UIUC Pre-Med Society"], ["Gym"], [(SU, MIDDAY), (SA, MORNING)]),
    ("bmiller6", "Ben Miller", MEDIA, "Advertising", "", S, OUTGOING, CASUAL, SMALL, True, True, True,
     ["Movies", "Music", "Gaming", "Food"], ["Illini Media"], ["Movies"], [(SA, AFTERNOON), (SU, EVENING)]),
    ("zwang11", "Zoe Wang", LAS, "Mathematics", "Math Tutoring Center - Tutor", F, RESERVED, DEEP, ONE, True, False,
     True, ["Reading", "Art", "Technology"], [], ["Reading"], [(SU, AFTERNOON), (SA, MORNING)]),
    ("ifisch3", "Isaac Fischer", ENG, "Aerospace Engineering", "", S, BALANCED, ACTIVITY, SMALL, True, True, False,
     ["Technology", "Gaming", "Outdoors"], ["Illini Robotics", "Engineers Without Borders"], ["Technology"],
     [(SA, AFTERNOON), (SU, MORNING)]),
    ("gmensah2", "Grace Mensah", BUS, "Marketing", "Illini Union Bookstore - Sales Associate", F, OUTGOING, CASUAL,
     EITHER, True, False, True, ["Travel", "Food", "Photography"], ["Business Illini"], ["Travel"],
     [(SU, AFTERNOON), (SA, EVENING)]),
    ("rmehta31", "Rohan Mehta", ENG, "Computer Science", "", S, OUTGOING, ACTIVITY, SMALL, True, True, True,
     ["Basketball", "Gaming", "Gym", "Technology"], ["Indian Students Association", "UIUC Esports"], ["Basketball"],
     [(SA, AFTERNOON), (SA, EVENING)]),
    ("ejohns12", "Emma Johnson", MEDIA, "Journalism", "The Daily Illini - Photographer", F, BALANCED, DEEP, ONE, False,
     True, True, ["Photography", "Reading", "Travel"], ["Illini Media"], ["Photography"], [(SU, AFTERNOON), (SU, MIDDAY)]),
    ("dcohen5", "David Cohen", LAS, "History", "", S, BALANCED, CASUAL, SMALL, True, False, True,
     ["Movies", "Reading", "Food"], ["Illinois Student Government"], ["Movies"], [(SA, MIDDAY), (SU, EVENING)]),
    ("creyes4", "Camila Reyes", FAA, "Dance", "", S, VERY_SOCIAL, ACTIVITY, SMALL, True, True, True,
     ["Music", "Fitness", "Art"], ["UIUC Dance Marathon"], ["Music"], [(SA, AFTERNOON), (SU, MIDDAY)]),
    ("nbaker2", "Noah Baker", AHS, "Recreation, Sport and Tourism", "Campus Rec - Climbing Wall Staff", S, OUTGOING,
     ACTIVITY, SMALL, True, False, True, ["Outdoors", "Gym", "Basketball"], [], ["Outdoors"], [(SA, MORNING), (SU, MORNING)]),
    ("jli27", "Jia Li", ENG, "Industrial Engineering", "", F, QUIET, DEEP, ONE, True, False, False,
     ["Reading", "Gaming", "Movies"], [], ["Reading"], [(SU, MIDDAY), (SU, AFTERNOON)]),
    ("kosei2", "Kwame Osei", BUS, "Finance", "", S, BALANCED, CASUAL, EITHER, True, True, True,
     ["Basketball", "Food", "Travel"], ["Business Illini"], ["Basketball"], [(SA, AFTERNOON), (SU, EVENING)]),
    ("lschmid4", "Lena Schmidt", LAS, "Chemistry", "", F, RESERVED, DEEP, ONE, True, True, True,
     ["Outdoors", "Reading", "Photography"], ["UIUC Pre-Med Society"], ["Outdoors"], [(SA, MORNING), (SU, AFTERNOON)]),
    ("arivera6", "Andre Rivera", MEDIA, "Media and Cinema Studies", "", S, OUTGOING, CASUAL, SMALL, True, False, True,
     ["Movies", "Photography", "Music"], ["Illini Media"], ["Movies"], [(SA, EVENING), (SU, AFTERNOON)]),
    ("pshah9", "Pooja Shah", ENG, "Bioengineering", "", F, BALANCED, CASUAL, ONE, True, True, True,
     ["Gym", "Fitness", "Food", "Travel"], ["Indian Students Association", "UIUC Pre-Med Society"], ["Gym"],
     [(SU, MIDDAY), (SA, MORNING)]),
    ("tnguyen8", "Thanh Nguyen", ENG, "Computer Science", "Siebel CS - Course Assistant", S, RESERVED, ACTIVITY, SMALL,
     False, True, False, ["Gaming", "Technology", "Music"], ["UIUC Esports"], ["Gaming"], [(SA, AFTERNOON), (SU, EVENING)]),
    ("mbrown15", "Mia Brown", FAA, "Architecture", "", F, QUIET, DEEP, ONE, True, False, True,
     ["Art", "Reading", "Outdoors"], ["Habitat for Humanity UIUC"], ["Art"], [(SU, MIDDAY), (SU, MORNING)]),
    ("ojames3", "Owen James", AHS, "Kinesiology", "", S, VERY_SOCIAL, ACTIVITY, SMALL, True, False, True,
     ["Gym", "Fitness", "Basketball", "Gaming"], [], ["Gym"], [(SA, AFTERNOON), (SA, MORNING)]),
    ("fahmed5", "Fatima Ahmed", LAS, "Psychology", "Counseling Center - Peer Mentor", F, BALANCED, DEEP, ONE, True,
     False, True, ["Reading", "Food", "Art"], ["Illinois Student Government"], ["Reading"], [(SU, AFTERNOON), (SA, MIDDAY)]),
    ("lwilson4", "Liam Wilson", BUS, "Information Systems", "", S, BALANCED, ACTIVITY, EITHER, True, True, False,
     ["Technology", "Gaming", "Basketball"], ["Business Illini", "UIUC Esports"], ["Technology"],
     [(SA, AFTERNOON), (SU, MIDDAY)]),
    ("nrao6", "Nisha Rao", ENG, "Materials Science", "", F, QUIET, CASUAL, ONE, True, True, True,
     ["Reading", "Photography", "Music"], ["Indian Students Association"], ["Photography"],
     [(SU, AFTERNOON), (SU, EVENING)]),
    ("jcarter7", "Jasmine Carter", MEDIA, "Advertising", "", S, OUTGOING, CASUAL, SMALL, True, False, True,
     ["Food", "Music", "Travel", "Photography"], ["UIUC Dance Marathon"], ["Food"], [(SA, EVENING), (SA, MIDDAY)]),
    ("spark12", "Sam Park", ENG, "Mechanical Engineering", "", S, BALANCED, ACTIVITY, SMALL, True, True, True,
     ["Gym", "Outdoors", "Technology"], ["Illini Robotics"], ["Gym"], [(SA, MORNING), (SA, AFTERNOON)]),
]
STUDENTS += [row[:12] for row in FALL_STUDENTS]
PICKS |= {row[0]: row[12:15] for row in FALL_STUDENTS}
AVAILABILITY |= {row[0]: row[15] for row in FALL_STUDENTS}
# Three sign-ups a day from 24 August, before the week of the current matches.
ONBOARDED |= {row[0]: date(2026, 8, 24) + timedelta(days=i // 3) for i, row in enumerate(FALL_STUDENTS)}

# Course staff accounts. The assignments ask for an instructor login with
# exactly these credentials on the deployed site. Student sign-in arrives
# with SSO later, so students get no password at all.
STAFF_USERNAMES = ["tester", "mohitg2"]
STAFF_PASSWORD = "uiuc12345"  # noqa: S105 - published by the course


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
        # After the three matches above, so they keep ids 1-3.
        self._seed_history(profiles, interests, locations)
        self._seed_staff()
        call_command("seed_ai_logs", stdout=self.stdout)  # P1-A10: /analytics/
        self._summarise()

    # -- catalogue ------------------------------------------------------
    def _seed_interests(self):
        catalogue = {}
        for names, category in (
            (HOBBIES, InterestCategory.HOBBY),
            (RSOS, InterestCategory.RSO),
            (ACTIVITIES, InterestCategory.ACTIVITY),
            (LATER_HOBBIES, InterestCategory.HOBBY),
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
                    "onboarding_completed_at": timezone.make_aware(
                        datetime.combine(ONBOARDED[net_id], time(19, 0))),
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

    def _seed_history(self, profiles, interests, locations):
        """Past weekly cycles from HISTORY, with check-ins and feedback.

        Match reasons and fit scores are derived from what each participant
        shares with the others, so they stay consistent with PICKS.
        """
        tz = timezone.get_current_timezone()
        activities = {name: obj for (name, category), obj in interests.items()
                      if category == InterestCategory.ACTIVITY}
        picks = {net_id: set(hobbies) | set(rsos)
                 for net_id, (hobbies, rsos, _) in PICKS.items()}

        for (week, code, kind, day, start, venue, activity, status,
             members, ratings) in HISTORY:
            when = timezone.make_aware(
                datetime.combine(week + timedelta(days=day), start), tz)
            match, _ = Match.objects.update_or_create(
                check_in_code=code,
                defaults={
                    "connection_type": kind,
                    "week_start": week,
                    "scheduled_for": when,
                    "location": locations[venue],
                    "suggested_activity": activities[activity],
                    "status": status,
                },
            )
            declined = DECLINED.get(code, set())
            for i, net_id in enumerate(members):
                others = set().union(*(picks[m] for m in members if m != net_id))
                shared = sorted(picks[net_id] & others)
                accepted = net_id not in declined
                participant, _ = MatchParticipant.objects.update_or_create(
                    match=match,
                    profile=profiles[net_id],
                    defaults={
                        "response": (ParticipantResponse.ACCEPTED if accepted
                                     else ParticipantResponse.DECLINED),
                        "compatibility_score": round(
                            min(97.0, 70.0 + 6.5 * len(shared)) - 0.35 * i, 2),
                        "match_reason": (", ".join(shared[:3]) if shared else
                                         "Same free time and conversation style"),
                        "checked_in_at": (when - timedelta(minutes=5)
                                          if status == DONE and accepted else None),
                    },
                )
                if net_id in ratings:
                    rating = ratings[net_id]
                    ExperienceFeedback.objects.update_or_create(
                        participant=participant,
                        defaults={
                            "rating": rating,
                            "enjoyed_conversation": rating >= 4,
                            "enjoyed_shared_interests": bool(shared),
                            "enjoyed_activity": rating == 5,
                            "felt_comfortable": rating >= 3,
                            "wants_to_stay_connected": rating >= 4,
                            "private_note": "",
                        },
                    )
        self.stdout.write(
            f"Match history: {len(HISTORY)} past matches | matches in total: "
            f"{Match.objects.count()}"
        )

    def _seed_staff(self):
        """Create the course staff accounts, without resetting a changed password."""
        for username in STAFF_USERNAMES:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_staff": True, "is_superuser": True},
            )
            if created:
                user.set_password(STAFF_PASSWORD)
                user.save()
            elif not (user.is_staff and user.is_superuser):
                user.is_staff = user.is_superuser = True
                user.save(update_fields=["is_staff", "is_superuser"])
        self.stdout.write(f"Staff accounts: {', '.join(STAFF_USERNAMES)}")

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
        staff = User.objects.filter(is_staff=True).count()
        self.stdout.write(f"  {'staff accounts':24s} {staff:>4} rows")
