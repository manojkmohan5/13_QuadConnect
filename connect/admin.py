"""
Django Admin configuration for QuadConnect.

Every model is registered so that the data model can be validated by hand:
records can be created and edited, and each relationship is visible and
selectable from the parent object via inlines.
"""

from django.contrib import admin

from .models import (
    AvailabilitySlot,
    CampusLocation,
    ExperienceFeedback,
    Interest,
    Match,
    MatchParticipant,
    ProfileInterest,
    StudentProfile,
)

# ---------------------------------------------------------------------------
# Inlines - make relationships editable from the parent record.
# ---------------------------------------------------------------------------


class ProfileInterestInline(admin.TabularInline):
    """Edit a student's interest selections from the profile page."""

    model = ProfileInterest
    extra = 1
    autocomplete_fields = ["interest"]


class AvailabilitySlotInline(admin.TabularInline):
    """Edit a student's weekend availability from the profile page."""

    model = AvailabilitySlot
    extra = 1


class MatchParticipantInline(admin.TabularInline):
    """Add or remove students from a match on the match page."""

    model = MatchParticipant
    extra = 1
    autocomplete_fields = ["profile"]
    readonly_fields = ["checked_in_at"]


class ExperienceFeedbackInline(admin.StackedInline):
    """Attach the private post-experience feedback to its participant row."""

    model = ExperienceFeedback
    extra = 0
    can_delete = True


# ---------------------------------------------------------------------------
# Model admins
# ---------------------------------------------------------------------------


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "net_id",
        "college",
        "preferred_connection",
        "social_energy",
        "is_sso_verified",
    )
    list_filter = (
        "preferred_connection",
        "conversation_style",
        "group_preference",
        "is_sso_verified",
        "college",
    )
    search_fields = ("full_name", "net_id", "illinois_email", "department")
    autocomplete_fields = ["user"]
    inlines = [ProfileInterestInline, AvailabilitySlotInline]
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Verified identity (Screen 1)", {
            "fields": ("user", "net_id", "illinois_email", "full_name",
                       "is_sso_verified"),
        }),
        ("Academic context (Screen 2)", {
            "fields": ("college", "department", "part_time_job"),
        }),
        ("Connection type (Screen 3)", {
            "fields": ("preferred_connection",),
        }),
        ("Social preferences (Screen 4)", {
            "fields": ("social_energy", "conversation_style",
                       "group_preference", "prefers_same_age",
                       "prefers_shared_rso", "open_to_other_departments"),
        }),
        ("Onboarding", {
            "fields": ("onboarding_completed_at", "created_at"),
        }),
    )


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "selection_count")
    list_filter = ("category", "is_active")
    search_fields = ("name",)

    @admin.display(description="Times selected")
    def selection_count(self, obj):
        return obj.profile_links.count()


@admin.register(ProfileInterest)
class ProfileInterestAdmin(admin.ModelAdmin):
    list_display = ("profile", "interest", "is_primary", "selected_at")
    list_filter = ("is_primary", "interest__category")
    search_fields = ("profile__net_id", "profile__full_name", "interest__name")
    autocomplete_fields = ["profile", "interest"]


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("profile", "weekday", "time_block")
    list_filter = ("weekday", "time_block")
    search_fields = ("profile__net_id", "profile__full_name")
    autocomplete_fields = ["profile"]


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "street_address", "is_indoor", "capacity",
                    "is_approved", "hosted_matches")
    list_filter = ("is_indoor", "is_approved")
    search_fields = ("name", "street_address")

    @admin.display(description="Matches hosted")
    def hosted_matches(self, obj):
        return obj.matches.count()


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("check_in_code", "connection_type", "week_start",
                    "scheduled_for", "location", "status", "headcount")
    list_filter = ("connection_type", "status", "week_start", "location")
    search_fields = ("check_in_code", "location__name")
    date_hierarchy = "scheduled_for"
    autocomplete_fields = ["location", "suggested_activity"]
    inlines = [MatchParticipantInline]

    @admin.display(description="Participants")
    def headcount(self, obj):
        return obj.participants.count()


@admin.register(MatchParticipant)
class MatchParticipantAdmin(admin.ModelAdmin):
    list_display = ("profile", "match", "response", "compatibility_score",
                    "checked_in_at")
    list_filter = ("response", "match__connection_type", "match__week_start")
    search_fields = ("profile__net_id", "profile__full_name",
                     "match__check_in_code")
    autocomplete_fields = ["match", "profile"]
    inlines = [ExperienceFeedbackInline]


@admin.register(ExperienceFeedback)
class ExperienceFeedbackAdmin(admin.ModelAdmin):
    list_display = ("participant", "rating", "wants_to_stay_connected",
                    "submitted_at")
    list_filter = ("rating", "wants_to_stay_connected", "felt_comfortable")
    search_fields = ("participant__profile__net_id",
                     "participant__profile__full_name")
    autocomplete_fields = ["participant"]
    readonly_fields = ("submitted_at",)


admin.site.site_header = "QuadConnect Administration"
admin.site.site_title = "QuadConnect Admin"
admin.site.index_title = "Verified campus social discovery - data model"
