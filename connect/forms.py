"""
Forms for the connect app.

Every user input goes through a Django form, so validation, labels, help
text and error messages are defined once. Rendered with
{{ field.as_field_group }}, each field gets a <label>, and Django adds
aria-describedby (help text and error) and aria-invalid="true" on error.

    StudentSearchForm             GET   /search/     roster filters, shareable URL
    NetIDLookupForm               POST  /search/     NetID lookup, kept out of the URL
    CampusLocationSuggestionForm  POST  /locations/  suggest a venue (creates a row)
    ProfileIntroForm              POST  /ai/profile-assistant/   free-text intro for the local model
    MatchNoteForm                 POST  /matches/<id>/ai-welcome/  optional note for the hybrid pipeline
"""

import re

from allauth.account.forms import LoginForm as AllauthLoginForm
from django import forms

from .models import CampusLocation, ConnectionType, StudentProfile

NETID_RE = re.compile(r"[a-z][a-z0-9]*")


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
        net_id = self.cleaned_data["net_id"].strip().lower()
        if not NETID_RE.fullmatch(net_id):
            raise forms.ValidationError(
                "A NetID is letters followed by optional digits, like "
                "jordan4. Remove any spaces, symbols or @illinois.edu."
            )
        return net_id


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


class ProfileIntroForm(QuadForm):
    """P1-A6: the free-text intro the local model reads. Submitted with POST."""

    text = forms.CharField(
        label="Tell us about yourself",
        min_length=10,
        max_length=600,
        widget=forms.Textarea(attrs={"rows": 5, "maxlength": 600}),
        help_text="Two or three sentences: what you enjoy, how you like to talk, "
                  "and whether you prefer one person or a small group (10-600 characters).",
        error_messages={
            "required": "Write a few words about yourself first.",
            "min_length": "Write a little more: at least 10 characters.",
            "max_length": "Keep it to 600 characters or fewer.",
        },
    )


class MatchNoteForm(QuadForm):
    """P1-A6: an optional note to personalise a match's welcome message."""

    note = forms.CharField(
        label="Anything you would like your match to know? (optional)",
        required=False,
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 300}),
        help_text="For example: \"I'm a bit nervous but love basketball.\" "
                  "Your note is read by our own model on this server. It is never sent to the "
                  "message-writing service; only the interests it finds are.",
        error_messages={"max_length": "Keep it to 300 characters or fewer."},
    )
