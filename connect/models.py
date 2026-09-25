"""
Data model for QuadConnect - a verified campus social discovery platform.

The eight models below map onto the nine screens documented in the team's
wireframe deck, so that every stored field has a visible reason to exist:

    Screen 1 (UIUC SSO Login) .............. StudentProfile
    Screen 2 (Interests & Hobbies) ......... Interest, ProfileInterest
    Screen 3 (Choose Connection Type) ...... StudentProfile.preferred_connection
    Screen 4 (Social Preferences) .......... StudentProfile (preference fields)
    Screen 5 (Availability) ................ AvailabilitySlot
    Screen 6/7 (Friend / Squad Match) ...... Match, MatchParticipant
    Screen 8 (Meeting & Check-in) .......... CampusLocation, MatchParticipant
    Screen 9 (Post-Experience Feedback) .... ExperienceFeedback
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse

# ---------------------------------------------------------------------------
# Choice vocabularies. Kept as TextChoices rather than free text so that the
# matching engine can compare preferences without normalising strings.
# ---------------------------------------------------------------------------


class ConnectionType(models.TextChoices):
    """The two experience formats offered by the current prototype."""

    FRIEND = "FRIEND", "Friend Connect (1-on-1)"
    SQUAD = "SQUAD", "Squad Connect (4-8 students)"


class SocialEnergy(models.IntegerChoices):
    """Screen 4 social-energy slider, stored as an ordered scale."""

    QUIET = 1, "Quiet / Low-key"
    RESERVED = 2, "Somewhat quiet"
    BALANCED = 3, "Balanced"
    OUTGOING = 4, "Fairly social"
    VERY_SOCIAL = 5, "Very social"


class ConversationStyle(models.TextChoices):
    """Screen 4 conversation-style radio group."""

    CASUAL = "CASUAL", "Casual conversations"
    DEEP = "DEEP", "Deep conversations"
    ACTIVITY = "ACTIVITY", "Activity-focused"


class GroupPreference(models.TextChoices):
    """Screen 4 group-size radio group."""

    ONE = "ONE", "One person"
    SMALL = "SMALL", "Small group (3-5)"
    EITHER = "EITHER", "Either"


class Weekday(models.IntegerChoices):
    """Weekend days offered on Screen 5. ISO numbering (Mon=1)."""

    SATURDAY = 6, "Saturday"
    SUNDAY = 7, "Sunday"


class TimeBlock(models.TextChoices):
    """The four two-hour windows offered on Screen 5."""

    MORNING = "10-12", "10 AM - 12 PM"
    MIDDAY = "12-14", "12 - 2 PM"
    AFTERNOON = "14-16", "2 - 4 PM"
    EVENING = "16-18", "4 - 6 PM"


class InterestCategory(models.TextChoices):
    """Interests are one catalogue split by category, not three tables."""

    HOBBY = "HOBBY", "Hobby / Interest"
    RSO = "RSO", "Registered Student Organization"
    ACTIVITY = "ACTIVITY", "Meeting activity"


class MatchStatus(models.TextChoices):
    """Lifecycle of a weekly match, driven by Screens 6-9."""

    PROPOSED = "PROPOSED", "Proposed to participants"
    CONFIRMED = "CONFIRMED", "Confirmed by participants"
    COMPLETED = "COMPLETED", "Meeting completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ParticipantResponse(models.TextChoices):
    """A single student's answer to their weekly match (Screens 6 and 7)."""

    PENDING = "PENDING", "Awaiting response"
    ACCEPTED = "ACCEPTED", "Accepted / attendance confirmed"
    DECLINED = "DECLINED", "Declined"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class StudentProfile(models.Model):
    """
    Represents a single SSO-verified UIUC student inside QuadConnect.

    This model exists because QuadConnect is a closed, student-only community:
    a Django User proves that someone signed in, but this profile is what
    proves they are a verified Illinois student, and it carries every matching
    signal collected during onboarding (Screens 1-4). It is kept separate from
    User rather than merged into it so that authentication can later be swapped
    for real Illinois Shibboleth SSO without touching product data.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        help_text="Account created by UIUC SSO sign-in.",
        # CASCADE: a profile describes exactly one account and is meaningless
        # once that account is gone. Keeping an orphan profile would leave
        # undeletable personal data stranded in the system.
    )
    net_id = models.CharField(
        max_length=32,
        unique=True,
        help_text="University NetID, e.g. jordan4. One profile per NetID.",
    )
    illinois_email = models.EmailField(
        unique=True,
        help_text="illinois.edu address returned by SSO.",
    )
    full_name = models.CharField(max_length=120)

    # --- Screen 2: academic context --------------------------------------
    college = models.CharField(
        max_length=120,
        help_text="e.g. Grainger College of Engineering.",
    )
    department = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional major or program, e.g. Computer Science.",
    )
    part_time_job = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional on/near-campus job used as a soft matching signal.",
    )

    # --- Screen 3: connection type ---------------------------------------
    preferred_connection = models.CharField(
        max_length=10,
        choices=ConnectionType.choices,
        default=ConnectionType.FRIEND,
    )

    # --- Screen 4: social preferences -------------------------------------
    social_energy = models.PositiveSmallIntegerField(
        choices=SocialEnergy.choices,
        default=SocialEnergy.BALANCED,
    )
    conversation_style = models.CharField(
        max_length=10,
        choices=ConversationStyle.choices,
        default=ConversationStyle.CASUAL,
    )
    group_preference = models.CharField(
        max_length=10,
        choices=GroupPreference.choices,
        default=GroupPreference.EITHER,
    )
    prefers_same_age = models.BooleanField(
        default=True,
        help_text="Screen 4: comfortable being matched within one year of age.",
    )
    prefers_shared_rso = models.BooleanField(
        default=False,
        help_text="Screen 4: weight shared RSO membership more heavily.",
    )
    open_to_other_departments = models.BooleanField(
        default=True,
        help_text="Screen 4: willing to meet students outside their college.",
    )

    interests = models.ManyToManyField(
        "Interest",
        through="ProfileInterest",
        related_name="profiles",
        blank=True,
    )

    is_sso_verified = models.BooleanField(
        default=True,
        help_text="False removes the student from the weekly matching pool.",
    )
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name", "net_id"]
        verbose_name = "Student profile"
        constraints = [
            # A NetID and its illinois.edu address must describe the same
            # person. This blocks a NetID being paired with someone else's
            # mailbox during a bad SSO import.
            models.UniqueConstraint(
                fields=["net_id", "illinois_email"],
                name="uniq_profile_netid_email",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.net_id})"

    def get_absolute_url(self):
        """This student's profile page, e.g. /students/3/.

        Templates link with {{ student.get_absolute_url }} instead of
        rebuilding the path, so the URL pattern is defined in one place.
        Django Admin also uses it for the "View on site" button.
        """
        return reverse("connect:student-detail", kwargs={"pk": self.pk})


class Interest(models.Model):
    """
    Represents one selectable interest, RSO, or meeting activity.

    This is the shared vocabulary behind the chip pickers on Screens 2 and 5.
    It exists as its own table rather than as free text on the profile so that
    "Gaming" means the same thing for every student, which is what makes
    overlap countable by the matching engine.
    """

    name = models.CharField(max_length=80)
    category = models.CharField(max_length=10, choices=InterestCategory.choices)
    is_active = models.BooleanField(
        default=True,
        help_text="Retire an option without deleting students' history.",
    )

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            # "Sports" may legitimately exist as both a hobby and an activity,
            # so uniqueness is per-category rather than global on name.
            models.UniqueConstraint(
                fields=["name", "category"],
                name="uniq_interest_name_per_category",
            ),
        ]

    def __str__(self):
        return f"{self.name} [{self.get_category_display()}]"


class ProfileInterest(models.Model):
    """
    Represents one student's selection of one interest.

    This explicit through-model exists so that a selection can carry weight:
    a student may star a handful of interests as the ones that matter most,
    and the matching engine scores those above their remaining picks.
    """

    profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="interest_links",
        # CASCADE: a selection has no meaning without the student who made it.
    )
    interest = models.ForeignKey(
        Interest,
        on_delete=models.PROTECT,
        related_name="profile_links",
        # PROTECT: deleting a catalogue entry that students already selected
        # would silently rewrite their profiles and corrupt past match
        # explanations. Retire it with is_active=False instead.
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Starred interest, weighted more heavily when matching.",
    )
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["profile", "-is_primary", "interest"]
        verbose_name = "Profile interest"
        constraints = [
            # A student cannot select the same interest twice.
            models.UniqueConstraint(
                fields=["profile", "interest"],
                name="uniq_interest_per_profile",
            ),
        ]

    def __str__(self):
        star = " *" if self.is_primary else ""
        return f"{self.profile.net_id} -> {self.interest.name}{star}"


class AvailabilitySlot(models.Model):
    """
    Represents one weekend time window a student marked as free (Screen 5).

    Availability is stored as rows rather than as a text blob because it is a
    hard constraint in matching: two students can only be paired if their slot
    rows intersect, and that intersection has to be a database query.
    """

    profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="availability_slots",
        # CASCADE: availability is worthless once the student is gone.
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    time_block = models.CharField(max_length=5, choices=TimeBlock.choices)

    class Meta:
        ordering = ["profile", "weekday", "time_block"]
        verbose_name = "Availability slot"
        constraints = [
            # Selecting "Saturday 2-4 PM" twice must be impossible, otherwise
            # duplicate rows would double-count overlap during matching.
            models.UniqueConstraint(
                fields=["profile", "weekday", "time_block"],
                name="uniq_slot_per_profile_day_block",
            ),
        ]

    def __str__(self):
        return (
            f"{self.profile.net_id}: {self.get_weekday_display()} "
            f"{self.get_time_block_display()}"
        )


class CampusLocation(models.Model):
    """
    Represents an approved public meeting place on the UIUC campus.

    Safety is a stated design principle: QuadConnect only ever schedules
    meetings at vetted, public, staffed locations. Holding that list in the
    database - rather than as a free-text address on each match - is what makes
    "approved location only" an enforceable rule instead of a promise.
    """

    name = models.CharField(max_length=120, unique=True)
    street_address = models.CharField(max_length=200)
    arrival_note = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. Main entrance, ground floor lobby.",
    )
    is_indoor = models.BooleanField(default=True)
    capacity = models.PositiveSmallIntegerField(
        default=8,
        validators=[MinValueValidator(2), MaxValueValidator(50)],
        help_text="Largest squad this location can comfortably seat.",
    )
    is_approved = models.BooleanField(
        default=True,
        help_text="Unapprove to stop scheduling here without losing history.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Campus location"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """This venue's page, e.g. /locations/2/. Staff-only if unapproved."""
        return reverse("connect:location-detail", kwargs={"pk": self.pk})


class Match(models.Model):
    """
    Represents one weekly scheduled experience produced by the matching cycle.

    QuadConnect deliberately produces a small number of scheduled meetings
    rather than an endless browsable feed, so a Match is the central object of
    the product: one real meeting, at one approved place, at one time, for one
    week (Screens 6, 7 and 8).
    """

    connection_type = models.CharField(
        max_length=10,
        choices=ConnectionType.choices,
    )
    week_start = models.DateField(
        help_text="Monday of the matching week this experience belongs to.",
    )
    scheduled_for = models.DateTimeField()
    location = models.ForeignKey(
        CampusLocation,
        on_delete=models.PROTECT,
        related_name="matches",
        # PROTECT: a past meeting must always be able to say where it happened.
        # Deleting a venue that hosted meetings would destroy that record, so
        # venues are retired with is_approved=False instead.
    )
    suggested_activity = models.ForeignKey(
        Interest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_for_matches",
        limit_choices_to={"category": InterestCategory.ACTIVITY},
        # SET_NULL: the suggested activity is a nice-to-have prompt, not part
        # of the meeting's identity. If the activity is removed the meeting is
        # still perfectly valid, it simply loses its suggestion.
    )
    status = models.CharField(
        max_length=10,
        choices=MatchStatus.choices,
        default=MatchStatus.PROPOSED,
    )
    check_in_code = models.CharField(
        max_length=12,
        unique=True,
        help_text="Short code shown on Screen 8, e.g. QC-4827.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-week_start", "-scheduled_for"]
        verbose_name_plural = "Matches"

    def __str__(self):
        return (
            f"{self.get_connection_type_display()} at {self.location.name} "
            f"on {self.scheduled_for:%b %d %H:%M}"
        )

    def get_absolute_url(self):
        """This match's page, e.g. /matches/5/."""
        return reverse("connect:match-detail", kwargs={"pk": self.pk})


class MatchParticipant(models.Model):
    """
    Represents one student's place in one match: the join row between a
    student and a meeting.

    It exists as its own model because membership carries state that belongs to
    the pairing rather than to either side - whether that student accepted,
    when they checked in on Screen 8, and why they were matched at all. The
    stored explanation is what the "Why you matched" panel on Screen 6 renders.
    """

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="participants",
        # CASCADE: a participant row describes a place inside one meeting. If
        # the meeting is deleted, the row describes nothing.
    )
    profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="match_participations",
        # PROTECT: deleting a student mid-cycle would silently shrink a squad
        # that other students are still planning to attend. The student must
        # first be withdrawn (response=DECLINED), which is an explicit act.
    )
    response = models.CharField(
        max_length=10,
        choices=ParticipantResponse.choices,
        default=ParticipantResponse.PENDING,
    )
    compatibility_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0-100 fit score against the rest of this match.",
    )
    match_reason = models.CharField(
        max_length=250,
        blank=True,
        help_text="Human-readable reasons, e.g. Basketball, Gaming, Coffee.",
    )
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when the student enters the code on Screen 8.",
    )

    class Meta:
        ordering = ["match", "-compatibility_score", "profile"]
        verbose_name = "Match participant"
        constraints = [
            # A student can appear in a given match exactly once.
            models.UniqueConstraint(
                fields=["match", "profile"],
                name="uniq_participant_per_match",
            ),
        ]

    def __str__(self):
        return f"{self.profile.net_id} in match {self.match_id} ({self.response})"


class ExperienceFeedback(models.Model):
    """
    Represents the private post-meeting feedback one student left (Screen 9).

    Feedback is one-to-one with a participant row rather than with a student,
    because a student leaves at most one review per experience. It is private
    by design: it feeds future matching quality and the mutual opt-in that
    creates a lasting connection, and it is never shown to the other party.
    """

    participant = models.OneToOneField(
        MatchParticipant,
        on_delete=models.CASCADE,
        related_name="feedback",
        # CASCADE: feedback is about one specific attendance. Without that
        # attendance record the rating cannot be attributed to anything.
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall 1-5 star rating of the experience.",
    )
    enjoyed_conversation = models.BooleanField(default=False)
    enjoyed_shared_interests = models.BooleanField(default=False)
    enjoyed_activity = models.BooleanField(default=False)
    felt_comfortable = models.BooleanField(default=False)
    wants_to_stay_connected = models.BooleanField(
        default=False,
        help_text="Mutual opt-in: a connection forms only if both sides agree.",
    )
    private_note = models.TextField(
        blank=True,
        help_text="Never shown to other participants.",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Experience feedback"
        verbose_name_plural = "Experience feedback"

    def __str__(self):
        return f"{self.participant.profile.net_id}: {self.rating}/5"
