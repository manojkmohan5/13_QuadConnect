"""
Forms for the connect app.

Every user input goes through a Django form, so validation, labels, help
text and error messages are defined once. Rendered with
{{ field.as_field_group }}, each field gets a <label>, and Django adds
aria-describedby (help text and error) and aria-invalid="true" on error.

    StudentSearchForm             GET   /search/     roster filters, shareable URL
    NetIDLookupForm               POST  /search/     NetID lookup, kept out of the URL
    CampusLocationSuggestionForm  POST  /locations/  suggest a venue (creates a row)
    ProfileForm                   POST  /profile/    set up or edit your own profile
    MeetForm                      POST  /meet/       sign up for the weekend's matching
    FeedbackForm                  POST  /matches/<pk>/feedback/  after a meetup
"""

import re
from io import BytesIO
from uuid import uuid4

from allauth.account.forms import LoginForm as AllauthLoginForm
from allauth.account.models import EmailAddress
from django import forms
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from PIL import Image, ImageOps

from .models import (
    AvailabilitySlot,
    CampusLocation,
    ConnectionType,
    ExperienceFeedback,
    Interest,
    InterestCategory,
    ProfileInterest,
    StudentProfile,
    TimeBlock,
    Weekday,
)

NETID_RE = re.compile(r"[a-z][a-z0-9]*")

# Every UIUC college and school a student can belong to. The six the seeded
# students are in keep the seed's spelling, so a new student shares their
# filter on the roster and their bar in the charts.
COLLEGES = [
    "Carle Illinois College of Medicine",
    "College of Agricultural, Consumer and Environmental Sciences",
    "College of Applied Health Sciences",
    "College of Education",
    "College of Fine & Applied Arts",
    "College of Law",
    "College of Liberal Arts & Sciences",
    "College of Media",
    "College of Veterinary Medicine",
    "Division of General Studies",
    "Gies College of Business",
    "Grainger College of Engineering",
    "School of Information Sciences",
    "School of Labor and Employment Relations",
    "School of Social Work",
]


def normalise_net_id(value):
    """A NetID as stored: trimmed, lower case, letters then optional digits.
    Shared by the NetID lookup and the profile form, so both explain a bad
    one the same way."""
    net_id = value.strip().lower()
    if not NETID_RE.fullmatch(net_id):
        raise forms.ValidationError(
            "A NetID is letters followed by optional digits, like "
            "jordan4. Remove any spaces, symbols or @illinois.edu."
        )
    return net_id


class QuadForm(forms.Form):
    """Base form: labels read "College", not Django's default "College:"."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class StudentSearchForm(QuadForm):
    """Roster search. Submitted with GET, so each search has its own URL."""

    q = forms.CharField(
        label="Name or interest",
        required=False,
        max_length=80,
        help_text="Part of a name or an interest, e.g. gaming or Chen.",
    )
    college = forms.ChoiceField(
        label="College",
        required=False,
        error_messages={
            "invalid_choice": "Pick a college from the list. "
                              "\"%(value)s\" is not one of them.",
        },
    )
    connection = forms.ChoiceField(
        label="Connection type",
        required=False,
        choices=[("", "Any type"), *ConnectionType.choices],
        error_messages={
            "invalid_choice": "Pick Friend Connect or Squad Connect. "
                              "\"%(value)s\" is not a connection type.",
        },
    )
    venue = forms.ChoiceField(
        label="Has met at",
        required=False,
        error_messages={
            "invalid_choice": "Pick an approved venue from the list. "
                              "\"%(value)s\" is not one of them.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per request from the data, so a new college or venue shows
        # up without a code change.
        colleges = (StudentProfile.objects.order_by("college")
                    .values_list("college", flat=True).distinct())
        self.fields["college"].choices = [
            ("", "Any college"), *((c, c) for c in colleges)]
        venues = (CampusLocation.objects.filter(is_approved=True)
                  .order_by("name").values_list("name", flat=True))
        self.fields["venue"].choices = [
            ("", "Any venue"), *((v, v) for v in venues)]


class NetIDLookupForm(QuadForm):
    """Find one student by NetID.

    Submitted with POST, so the NetID travels in the request body. It
    never appears in the URL, and so never in browser history, server
    access logs, or the Referer header sent when the next link is clicked.
    """

    net_id = forms.CharField(
        label="NetID",
        max_length=32,
        help_text="Letters, then optional digits, e.g. jordan4.",
        error_messages={"required": "Enter a NetID to look up, e.g. jordan4."},
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "autocapitalize": "none",
            "spellcheck": "false",
        }),
    )

    def clean_net_id(self):
        return normalise_net_id(self.cleaned_data["net_id"])


class CampusLocationSuggestionForm(forms.ModelForm):
    """Suggest a new meeting venue. Creates an unapproved CampusLocation.

    `fields` is a whitelist: is_approved is deliberately absent, so no
    POST can approve its own suggestion, even one hand-crafted to include
    is_approved=on. The view saves every suggestion as unapproved; staff
    approve it in Django Admin.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        # The model's 2-50 validators do not reach the widget, which would
        # otherwise say min="0" (from PositiveSmallIntegerField) and no max.
        self.fields["capacity"].widget.attrs.update({"min": 2, "max": 50})

    class Meta:
        model = CampusLocation
        fields = ["name", "street_address", "arrival_note", "is_indoor", "capacity"]
        labels = {
            "name": "Venue name",
            "arrival_note": "Where to meet (optional)",
            "is_indoor": "Indoors",
            "capacity": "Seats",
        }
        help_texts = {
            "name": "A public, staffed place on or near campus.",
            "street_address": "e.g. 1401 W Green St, Urbana.",
            "arrival_note": "e.g. Main entrance, ground floor lobby.",
            "is_indoor": "Untick for an outdoor spot such as the Main Quad.",
            "capacity": "The largest group it seats comfortably, 2 to 50.",
        }
        error_messages = {
            "name": {
                "unique": "That venue is already listed or waiting for "
                          "review. Check the list above, or name a "
                          "different place.",
                "required": "Enter the venue's name, e.g. Illini Union.",
            },
            "street_address": {
                "required": "Enter a street address so students can find "
                            "it, e.g. 1401 W Green St, Urbana.",
            },
            "capacity": {
                "required": "Enter how many people it seats, from 2 to 50.",
                "invalid": "Enter a whole number of seats, from 2 to 50.",
                "min_value": "A meetup needs at least 2 seats. Enter 2 to 50.",
                "max_value": "Squads are small; enter 50 seats or fewer.",
            },
        }

    def clean_name(self):
        # "  illini union " must collide with "Illini Union", not slip past
        # the unique check as a near-duplicate.
        name = " ".join(self.cleaned_data["name"].split())
        if CampusLocation.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError(
                self.Meta.error_messages["name"]["unique"])
        return name


class LoginForm(AllauthLoginForm):
    """django-allauth's login form without its "Forgot your password?" link
    (P1-A5). The host has no mail server, so a reset email could never
    arrive. Staff can set a new password in Django Admin. The labels say
    what to type ("Username or email", not allauth's bare "Login"). Wired
    in with ACCOUNT_FORMS in settings."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].help_text = ""
        self.fields["login"].label = "Username or email"
        self.fields["remember"].label = "Remember me"


def _picks(widget):
    """A set of choices drawn as pills (class "picks" in the stylesheet)."""
    return widget(attrs={"class": "picks"})


MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 50_000_000  # a 48-megapixel phone photo fits; a small file that unpacks to more does not
PHOTO_SIDE = 800  # pixels, the longer side


def _photo_jpeg(upload):
    """The uploaded photo as we keep it: upright, at most 800 px a side, as a
    JPEG under a random name. Saving a new JPEG drops the original's
    metadata, which on a phone photo can include where it was taken."""
    upload.seek(0)
    with Image.open(upload) as original:
        if original.width * original.height > MAX_PHOTO_PIXELS:
            raise forms.ValidationError("That photo is too big to use. Choose one under 50 megapixels.")
        image = ImageOps.exif_transpose(original)
        image.thumbnail((PHOTO_SIDE, PHOTO_SIDE))
        if image.mode in ("RGBA", "LA", "P"):  # see-through parts become white, not black
            image = image.convert("RGBA")
            backing = Image.new("RGB", image.size, "white")
            backing.paste(image, mask=image.getchannel("A"))
            image = backing
        out = BytesIO()
        image.convert("RGB").save(out, "JPEG", quality=85)
    return ContentFile(out.getvalue(), name=f"{uuid4().hex}.jpg")


class ProfileForm(forms.ModelForm):
    """Your own profile (connect/onboarding.py): who you are, how you like to
    meet, your interests and when you are free, the wireframes' onboarding
    screens on one page. The same form sets a profile up and edits it.

    The NetID is the one thing typed about the account: the illinois.edu
    address is made from it. The profile is marked verified only when the
    account has proved it owns that address (a Google sign-in with it); a
    NetID typed into a form proves nothing.

    The photo and the headline are optional. A photo is never kept as sent:
    _photo_jpeg() makes a smaller JPEG of it, under a new name, and the old
    file goes once the new one is saved, or the photo is removed.
    """

    TAKEN = ('Another account already has a profile with the NetID "{}". '
             "Check that you typed your own NetID.")

    college = forms.ChoiceField(
        label="College",
        choices=[("", "Choose your college"), *((c, c) for c in COLLEGES)],
        error_messages={"required": "Choose your college from the list."},
    )
    photo = forms.ImageField(
        label="Photo (optional)",
        required=False,
        help_text="A clear photo of you: JPEG, PNG or WebP, up to 5 MB. Every signed-in student can see it.",
        widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        error_messages={"invalid_image": "That file is not a photo we can open. "
                                         "Choose a JPEG, PNG or WebP image."},
    )
    remove_photo = forms.BooleanField(label="Remove my photo", required=False)
    hobbies = forms.ModelMultipleChoiceField(
        label="Hobbies and interests",
        required=False,
        queryset=Interest.objects.filter(category=InterestCategory.HOBBY, is_active=True).order_by("name"),
        widget=_picks(forms.CheckboxSelectMultiple),
    )
    clubs = forms.ModelMultipleChoiceField(
        label="Clubs (RSOs)",
        required=False,
        queryset=Interest.objects.filter(category=InterestCategory.RSO, is_active=True).order_by("name"),
        widget=_picks(forms.CheckboxSelectMultiple),
    )
    saturday = forms.MultipleChoiceField(
        label="Saturday", required=False, choices=TimeBlock.choices,
        widget=_picks(forms.CheckboxSelectMultiple))
    sunday = forms.MultipleChoiceField(
        label="Sunday", required=False, choices=TimeBlock.choices,
        widget=_picks(forms.CheckboxSelectMultiple))

    class Meta:
        model = StudentProfile
        fields = ["full_name", "headline", "net_id", "college", "department", "preferred_connection",
                  "group_preference", "social_energy", "conversation_style"]
        labels = {
            "full_name": "Your name",
            "headline": "Headline (optional)",
            "net_id": "NetID",
            "department": "Major or program (optional)",
            "preferred_connection": "How do you want to meet?",
            "group_preference": "Group size",
            "social_energy": "How social are you?",
            "conversation_style": "What do you like to talk about?",
        }
        help_texts = {
            "full_name": "As other students will see it.",
            "headline": "One line under your name, e.g. Always up for a board game night.",
            "net_id": "The part of your Illinois email before @illinois.edu, e.g. jordan4.",
            "department": "e.g. Information Sciences.",
        }
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "net_id": forms.TextInput(attrs={"autocapitalize": "none", "spellcheck": "false"}),
            "preferred_connection": _picks(forms.RadioSelect),
            "group_preference": _picks(forms.RadioSelect),
            "social_energy": _picks(forms.RadioSelect),
            "conversation_style": _picks(forms.RadioSelect),
        }
        error_messages = {
            "full_name": {"required": "Enter your name, as other students will see it."},
            "net_id": {"required": "Enter your NetID, e.g. jordan4."},
        }

    def __init__(self, *args, user, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        self.user = user
        for name in ("hobbies", "clubs"):  # "Gym", not "Gym [Hobby / Interest]"
            self.fields[name].label_from_instance = lambda interest: interest.name
        # In place of every format Pillow reads: these three, said plainly.
        self.fields["photo"].validators = [FileExtensionValidator(
            ["jpg", "jpeg", "png", "webp"], message="Choose a JPEG, PNG or WebP image.")]
        if self.instance.pk:  # editing: the answers already given
            chosen = list(self.instance.interest_links.values_list("interest_id", flat=True))
            self.initial["hobbies"] = self.initial["clubs"] = chosen
            for name, day in (("saturday", Weekday.SATURDAY), ("sunday", Weekday.SUNDAY)):
                self.initial[name] = list(self.instance.availability_slots
                                          .filter(weekday=day).values_list("time_block", flat=True))
        else:  # setting up: what the account already says (Google gives a name)
            self.initial["full_name"] = user.get_full_name()
            local, _, domain = user.email.partition("@")
            if domain.lower() == "illinois.edu":
                self.initial["net_id"] = local.lower()

    def clean_photo(self):
        upload = self.cleaned_data.get("photo")
        if not upload:
            return None
        if upload.size > MAX_PHOTO_BYTES:
            raise forms.ValidationError("That photo is over 5 MB. Choose a smaller one.")
        try:
            return _photo_jpeg(upload)
        except (OSError, ValueError) as error:  # opened, but could not be read to the end
            raise forms.ValidationError(self.fields["photo"].error_messages["invalid_image"]) from error

    def clean_net_id(self):
        net_id = normalise_net_id(self.cleaned_data["net_id"])
        taken = StudentProfile.objects.exclude(pk=self.instance.pk).filter(
            Q(net_id=net_id) | Q(illinois_email__iexact=f"{net_id}@illinois.edu"))
        if taken.exists():
            raise forms.ValidationError(self.TAKEN.format(net_id))
        return net_id

    def clean(self):
        data = super().clean()
        if not (data.get("hobbies") or data.get("clubs")):
            self.add_error("hobbies", "Pick at least one interest or club, so you can be "
                                      "matched with students who share it.")
        if not (data.get("saturday") or data.get("sunday")):
            self.add_error("saturday", "Pick at least one time on Saturday or Sunday. "
                                       "You are only matched for a time you are free.")
        return data

    def save(self):
        """Save the profile with its interests and free times, all or none."""
        profile = super().save(commit=False)
        profile.user = self.user
        profile.illinois_email = f"{profile.net_id}@illinois.edu"
        profile.is_sso_verified = EmailAddress.objects.filter(
            user=self.user, email__iexact=profile.illinois_email, verified=True).exists()
        profile.onboarding_completed_at = profile.onboarding_completed_at or timezone.now()
        old_photo = profile.photo.name
        if self.cleaned_data.get("photo"):
            profile.photo = self.cleaned_data["photo"]
        elif self.cleaned_data.get("remove_photo"):
            profile.photo = ""
        chosen = [*self.cleaned_data["hobbies"], *self.cleaned_data["clubs"]]
        free = [(Weekday.SATURDAY, block) for block in self.cleaned_data["saturday"]]
        free += [(Weekday.SUNDAY, block) for block in self.cleaned_data["sunday"]]
        with transaction.atomic():
            profile.save()
            # An interest kept keeps its row, and with it a star given in Admin.
            profile.interest_links.exclude(interest__in=chosen).delete()
            kept = set(profile.interest_links.values_list("interest_id", flat=True))
            ProfileInterest.objects.bulk_create(
                ProfileInterest(profile=profile, interest=interest)
                for interest in chosen if interest.pk not in kept)
            profile.availability_slots.all().delete()
            AvailabilitySlot.objects.bulk_create(
                AvailabilitySlot(profile=profile, weekday=day, time_block=block)
                for day, block in free)
            if old_photo and old_photo != profile.photo.name:  # replaced or removed
                transaction.on_commit(lambda: profile.photo.storage.delete(old_photo))
        return profile


class MeetForm(QuadForm):
    """Sign up for the coming weekend's matching (connect/meetups.py)."""

    connection_type = forms.ChoiceField(
        label="How do you want to meet this weekend?",
        choices=ConnectionType.choices,
        widget=_picks(forms.RadioSelect),
        help_text="1-on-1: the student who shares the most interests with you. "
                  "A group: 4 to 8 students who share one of your interests.",
        error_messages={"required": "Choose one-on-one or a group."},
    )


class FeedbackForm(forms.ModelForm):
    """How a meetup went (Screen 9). Private: nobody else in the match sees
    it. Only "stay connected" is ever acted on, and only when it is mutual."""

    rating = forms.TypedChoiceField(
        label="Your rating",
        choices=[(n, f"{n} star{'s' if n > 1 else ''}") for n in range(1, 6)],
        coerce=int,
        widget=_picks(forms.RadioSelect),
        error_messages={"required": "Choose from 1 to 5 stars."},
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    class Meta:
        model = ExperienceFeedback
        fields = ["rating", "enjoyed_conversation", "enjoyed_shared_interests", "enjoyed_activity",
                  "felt_comfortable", "wants_to_stay_connected", "private_note"]
        labels = {
            "enjoyed_conversation": "I enjoyed the conversation",
            "enjoyed_shared_interests": "We had interests in common",
            "enjoyed_activity": "I enjoyed what we did",
            "felt_comfortable": "I felt comfortable",
            "wants_to_stay_connected": "I'd like to stay connected",
            "private_note": "Anything else? (optional)",
        }
        help_texts = {
            "wants_to_stay_connected": "If they say so too, you each see the other's Illinois email.",
            "private_note": "Only QuadConnect staff read this.",
        }
