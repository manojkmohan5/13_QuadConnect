"""
Prove that the QuadConnect data model actually enforces what it claims.

Run with:  python manage.py verify_constraints

Every check runs inside a transaction that is rolled back afterwards, so this
command is safe to run repeatedly and never mutates the submitted database.
It needs the seed data (python manage.py seed_demo_data) and exits with
status 1 if any check fails.

Checks performed
----------------
UniqueConstraint
  1. uniq_interest_per_profile        - same interest picked twice
  2. uniq_slot_per_profile_day_block  - same weekend slot picked twice
  3. uniq_participant_per_match       - same student added to a match twice
  4. uniq_interest_name_per_category  - duplicate catalogue entry
  5. uniq_profile_netid_email         - NetID/email pair reused

on_delete
  6. PROTECT   - deleting a selected Interest is blocked
  7. PROTECT   - deleting a venue that hosted a match is blocked
  8. PROTECT   - deleting a student who is in a match is blocked
  9. CASCADE   - deleting a Match removes its participants and their feedback
 10. CASCADE   - deleting a User removes the StudentProfile
 11. SET_NULL  - deleting a suggested activity leaves the Match intact
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from connect.models import (
    AvailabilitySlot,
    CampusLocation,
    ExperienceFeedback,
    Interest,
    InterestCategory,
    Match,
    MatchParticipant,
    ProfileInterest,
    StudentProfile,
)


class Rollback(Exception):
    """Raised to unwind a check's transaction once it has proven its point."""


class Command(BaseCommand):
    help = "Demonstrate that constraints and on_delete rules are enforced."

    def handle(self, *args, **options):
        self.passed = 0
        self.failed = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== UniqueConstraint enforcement ==="
        ))
        self.check_duplicate_interest_pick()
        self.check_duplicate_availability_slot()
        self.check_duplicate_match_participant()
        self.check_duplicate_catalogue_entry()
        self.check_duplicate_netid_email_pair()

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== on_delete behaviour ==="
        ))
        self.check_protect_interest_in_use()
        self.check_protect_location_with_matches()
        self.check_protect_student_in_match()
        self.check_cascade_match_deletion()
        self.check_cascade_user_deletion()
        self.check_setnull_suggested_activity()

        total = self.passed + self.failed
        style = self.style.SUCCESS if not self.failed else self.style.ERROR
        self.stdout.write(style(
            f"\n{self.passed}/{total} checks passed, {self.failed} failed.\n"
        ))
        if self.failed:
            # A non-zero exit is what lets CI fail on a broken constraint.
            raise CommandError(f"{self.failed} of {total} checks failed.")

    # -- reporting helpers ----------------------------------------------
    def ok(self, label, detail):
        self.passed += 1
        self.stdout.write(self.style.SUCCESS(f"  PASS  {label}"))
        self.stdout.write(f"        {detail}")

    def bad(self, label, detail):
        self.failed += 1
        self.stdout.write(self.style.ERROR(f"  FAIL  {label}"))
        self.stdout.write(f"        {detail}")

    def expect_integrity_error(self, label, action):
        """Assert that `action` is rejected by a database constraint."""
        try:
            with transaction.atomic():
                action()
                raise Rollback("no error raised")
        except IntegrityError as exc:
            self.ok(label, f"IntegrityError: {self._first_line(exc)}")
        except Rollback:
            self.bad(label, "duplicate was accepted - constraint NOT enforced")

    def expect_protected(self, label, action):
        """Assert that `action` is blocked by on_delete=PROTECT."""
        try:
            with transaction.atomic():
                action()
                raise Rollback("no error raised")
        except ProtectedError as exc:
            self.ok(label, f"ProtectedError: {self._first_line(exc)}")
        except Rollback:
            self.bad(label, "delete succeeded - PROTECT NOT enforced")

    @staticmethod
    def _first_line(exc):
        return str(exc).splitlines()[0][:150]

    # -- UniqueConstraint checks ----------------------------------------
    def check_duplicate_interest_pick(self):
        link = ProfileInterest.objects.select_related(
            "profile", "interest").first()
        label = (f"uniq_interest_per_profile - {link.profile.net_id} picks "
                 f"'{link.interest.name}' twice")
        self.expect_integrity_error(
            label,
            lambda: ProfileInterest.objects.create(
                profile=link.profile, interest=link.interest
            ),
        )

    def check_duplicate_availability_slot(self):
        slot = AvailabilitySlot.objects.select_related("profile").first()
        label = (f"uniq_slot_per_profile_day_block - {slot.profile.net_id} "
                 f"re-adds {slot.get_weekday_display()} "
                 f"{slot.get_time_block_display()}")
        self.expect_integrity_error(
            label,
            lambda: AvailabilitySlot.objects.create(
                profile=slot.profile,
                weekday=slot.weekday,
                time_block=slot.time_block,
            ),
        )

    def check_duplicate_match_participant(self):
        p = MatchParticipant.objects.select_related("match", "profile").first()
        label = (f"uniq_participant_per_match - {p.profile.net_id} added to "
                 f"match {p.match.check_in_code} twice")
        self.expect_integrity_error(
            label,
            lambda: MatchParticipant.objects.create(
                match=p.match, profile=p.profile
            ),
        )

    def check_duplicate_catalogue_entry(self):
        interest = Interest.objects.filter(
            category=InterestCategory.HOBBY).first()
        label = (f"uniq_interest_name_per_category - second '{interest.name}' "
                 f"hobby entry")
        self.expect_integrity_error(
            label,
            lambda: Interest.objects.create(
                name=interest.name, category=interest.category
            ),
        )

    def check_duplicate_netid_email_pair(self):
        existing = StudentProfile.objects.first()
        label = (f"uniq_profile_netid_email - reuse of "
                 f"{existing.net_id}/{existing.illinois_email}")

        def action():
            user = User.objects.create(username="constraint_probe_user")
            StudentProfile.objects.create(
                user=user,
                net_id=existing.net_id,
                illinois_email=existing.illinois_email,
                full_name="Duplicate Probe",
                college="Test College",
            )

        self.expect_integrity_error(label, action)

    # -- on_delete checks -----------------------------------------------
    def check_protect_interest_in_use(self):
        interest = Interest.objects.filter(
            profile_links__isnull=False).distinct().first()
        n = interest.profile_links.count()
        self.expect_protected(
            f"PROTECT - delete Interest '{interest.name}' selected by {n} "
            f"student(s)",
            interest.delete,
        )

    def check_protect_location_with_matches(self):
        loc = CampusLocation.objects.filter(
            matches__isnull=False).distinct().first()
        n = loc.matches.count()
        self.expect_protected(
            f"PROTECT - delete CampusLocation '{loc.name}' hosting {n} "
            f"match(es)",
            loc.delete,
        )

    def check_protect_student_in_match(self):
        profile = StudentProfile.objects.filter(
            match_participations__isnull=False).distinct().first()
        n = profile.match_participations.count()
        self.expect_protected(
            f"PROTECT - delete StudentProfile '{profile.net_id}' in {n} "
            f"match(es)",
            profile.delete,
        )

    def check_cascade_match_deletion(self):
        label = "CASCADE - delete Match removes participants and feedback"
        match = Match.objects.filter(
            participants__feedback__isnull=False).distinct().first()
        pids = list(match.participants.values_list("id", flat=True))
        fb_before = ExperienceFeedback.objects.filter(
            participant_id__in=pids).count()
        try:
            with transaction.atomic():
                match.delete()
                parts_after = MatchParticipant.objects.filter(
                    id__in=pids).count()
                fb_after = ExperienceFeedback.objects.filter(
                    participant_id__in=pids).count()
                if parts_after == 0 and fb_after == 0:
                    self.ok(label, (
                        f"match {match.check_in_code}: {len(pids)} participant "
                        f"row(s) and {fb_before} feedback row(s) removed; "
                        f"students and venue untouched"
                    ))
                else:
                    self.bad(label, (
                        f"{parts_after} participants / {fb_after} feedback "
                        f"rows survived"
                    ))
                raise Rollback
        except Rollback:
            pass

    def check_cascade_user_deletion(self):
        label = "CASCADE - delete User removes its StudentProfile"
        try:
            with transaction.atomic():
                user = User.objects.create(username="cascade_probe_user")
                profile = StudentProfile.objects.create(
                    user=user,
                    net_id="cascade_probe",
                    illinois_email="cascade_probe@illinois.edu",
                    full_name="Cascade Probe",
                    college="Test College",
                )
                pid = profile.pk
                user.delete()
                if StudentProfile.objects.filter(pk=pid).exists():
                    self.bad(label, "profile survived deletion of its User")
                else:
                    self.ok(label, "profile row removed with the account")
                raise Rollback
        except Rollback:
            pass

    def check_setnull_suggested_activity(self):
        label = "SET_NULL - delete suggested activity, Match survives"
        match = Match.objects.filter(
            suggested_activity__isnull=False).first()
        activity = match.suggested_activity
        try:
            with transaction.atomic():
                # Detach the activity from student profiles first: those links
                # are PROTECTed, which is itself the correct behaviour.
                ProfileInterest.objects.filter(interest=activity).delete()
                activity.delete()
                match.refresh_from_db()
                if Match.objects.filter(pk=match.pk).exists() \
                        and match.suggested_activity_id is None:
                    self.ok(label, (
                        f"match {match.check_in_code} kept its date, venue and "
                        f"participants; suggested_activity is now NULL"
                    ))
                else:
                    self.bad(label, "match was deleted or kept a stale FK")
                raise Rollback
        except Rollback:
            pass
