"""
Joining QuadConnect: the account, then the profile.

An account is only a username and a password. The student is the
StudentProfile behind it, and until there is one, nobody can find them or be
matched with them. So every login or sign-up of a student without a profile
ends on /profile/ (AccountAdapter.post_login in adapters.py), whose form asks
for their NetID, interests and free weekend times. The same page edits the
profile later, and until it is filled in, every other page links to it
(base.html).

    SignupView   /accounts/signup/   allauth's sign-up, safe against a double click
    profile      /profile/           set up or edit your own profile
    media        /media/<path>       a profile photo, for signed-in users only
"""

from allauth.account.views import SignupView as AllauthSignupView
from django.contrib import messages
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import StudentProfile


class SignupView(AllauthSignupView):
    """allauth's sign-up page. A double click on "Create account" sends the
    form twice: both copies pass allauth's "username taken" check before
    either is saved, and the second save breaks the database's unique rule.
    That was a 500 page. Now it is the form again, saying what happened.

    Public like allauth's own view: it inherits the login_not_required
    dispatch."""

    def form_valid(self, form):
        try:
            with transaction.atomic():  # the whole sign-up, or none of it
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("username", (
                f'The username "{form.cleaned_data["username"]}" was taken a moment ago, '
                "perhaps by a second click on Create account. If that account is "
                "yours, log in. If not, choose another username."))
            return self.form_invalid(form)


def profile(request):
    """Your own profile as a form: empty to set it up, filled in to edit it.
    Saving opens the profile page, as other students see it, so a reload
    cannot send the form again (Post/Redirect/Get)."""
    mine = StudentProfile.objects.filter(user=request.user).first()
    new = mine is None
    posted = request.method == "POST"
    form = ProfileForm(request.POST if posted else None, request.FILES if posted else None,
                       instance=mine, user=request.user)
    if form.is_valid():
        try:
            mine = form.save()
        except IntegrityError:
            # A second click saved this new profile a moment ago. Otherwise
            # another account took the NetID while this one was being checked.
            mine = StudentProfile.objects.filter(user=request.user).first() if new else None
            if mine is None:
                form.add_error("net_id", ProfileForm.TAKEN.format(form.cleaned_data["net_id"]))
        if mine is not None:
            messages.success(request, "Your profile is set up. This is how other students see it."
                             if new else "Your profile is saved.")
            return redirect(mine)
    return render(request, "connect/profile_form.html", {"form": form, "new": new})


def media(request, path):
    """An uploaded file: a profile photo. Never a public file: like every
    view not marked public, this one needs a login (connect/middleware.py).
    The storage refuses a path that climbs out of MEDIA_ROOT (a 400).

    ponytail: Django sends the photo, and the middleware marks it never-cache
    as it does every signed-in page, so a photo is fetched again on each
    page. Fine at a campus's scale; let the web server send it (X-Sendfile)
    if that ever shows.
    """
    if not path.startswith("profile_photos/") or not default_storage.exists(path):
        raise Http404("No such photo.")
    return FileResponse(default_storage.open(path), content_type="image/jpeg")
