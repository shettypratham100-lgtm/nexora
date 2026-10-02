# ==========================================================
# IMPORTS
# ==========================================================

# Django shortcut functions.
#
# render()
#
#     Returns an HTML page.
#
# redirect()
#
#     Redirects the user to another URL.
#
from django.shortcuts import render, redirect
from django.urls import reverse


# Django authentication functions.
#
# authenticate()
#
#     Checks whether the username/email
#     and password are correct.
#
# login()
#
#     Creates a user session.
#
# logout()
#
#     Destroys the current session.
#
from django.contrib.auth import (

    authenticate,

    login,

    logout,

)


# Registration Form
#
from .forms import UserRegistrationForm, UserLoginForm

# ==========================================================
# EMAIL VERIFICATION HELPERS
# ==========================================================
#
# Reuses the exact same secure token mechanism Django's
# built-in "Forgot Password" flow uses (default_token_generator)
# -- no separate database table needed to track verification
# tokens, the token itself is derived from the user's current
# password hash + a timestamp, so it can't be reused or forged.
#
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

# ==========================================================
# USER MODEL
# ==========================================================
#
# Used to search users by Email
# during Login.
#
from django.contrib.auth.models import User

# ==========================================================
# DJANGO MESSAGES
# ==========================================================
#
# Displays notifications like:
#
# ✔ Registration Successful
#
# ✔ Login Successful
#
# ✔ Logout Successful
#
# ❌ Invalid Credentials
#
from django.contrib import messages

# ==========================================================
# SEND VERIFICATION EMAIL
# ==========================================================
#
# Builds a one-time verification link (same token pattern as
# Forgot Password) and emails it to the newly registered user.
#
def send_verification_email(request, user):

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    verify_url = request.build_absolute_uri(
        reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
    )

    message = render_to_string(
        "accounts/verification_email.html",
        {"user": user, "verify_url": verify_url},
    )

    send_mail(
        subject="Verify your Nexora account",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


# ==========================================================
# REGISTER VIEW
# ==========================================================
#
# Handles:
#
# GET
#
#     Display Registration Page
#
# POST
#
#     Validate form
#
#     Create User
#
#     Redirect Login
#
def register_view(request):

    # ------------------------------------------------------
    # User clicked Register button.
    # ------------------------------------------------------

    if request.method == "POST":

        form = UserRegistrationForm(

            request.POST

        )

        # ----------------------------------------------
        # Validate Form
        # ----------------------------------------------

        if form.is_valid():

            user = form.save()

            send_verification_email(request, user)

            messages.success(
                request,
                "Account created! Check your email to verify your account before logging in."
            )

            return redirect(
                "accounts:verification_pending"
            )

    # ------------------------------------------------------
    # First time opening Register page.
    # ------------------------------------------------------

    else:

        form = UserRegistrationForm()

    # ------------------------------------------------------
    # Send form to HTML page.
    # ------------------------------------------------------

    context = {

        "form": form,

    }

    return render(

        request,

        "accounts/register.html",

        context

    )


# ==========================================================
# LOGIN VIEW
# ==========================================================
#
# Allows login using either:
#
# • Username
#
# OR
#
# • Email
#
def login_view(request):

    # ------------------------------------------------------
    # User submitted Login Form.
    # ------------------------------------------------------

    if request.method == "POST":

        form = UserLoginForm(

            request.POST

        )

        if form.is_valid():

            username_or_email = form.cleaned_data[
                "username_or_email"
            ]

            password = form.cleaned_data[
                "password"
            ]

            # ------------------------------------------
            # Check whether input is Email.
            # ------------------------------------------

            try:

                user = User.objects.get(

                    email=username_or_email

                )

                username = user.username

            except User.DoesNotExist:

                username = username_or_email

            # ------------------------------------------
            # Authenticate User
            # ------------------------------------------

            authenticated_user = authenticate(

                request,

                username=username,

                password=password,

            )

            # ------------------------------------------
            # Login Success
            # ------------------------------------------

            if authenticated_user is not None:

                login(

                    request,

                    authenticated_user

                )

                messages.success(request,f"Welcome back {authenticated_user.first_name}!")

                return redirect("dashboard:dashboard")

            # ------------------------------------------
            # Login Failed
            # ------------------------------------------
            #
            # authenticate() returns None both for wrong
            # credentials AND for a correct password on an
            # inactive (unverified) account. We check which
            # case it is here to give a more helpful message.
            # ------------------------------------------

            try:
                attempted_user = User.objects.get(username=username)
            except User.DoesNotExist:
                attempted_user = None

            if attempted_user is not None and not attempted_user.is_active \
                    and attempted_user.check_password(password):

                messages.warning(
                    request,
                    "Your account isn't verified yet. "
                    "Check your email for the verification link, or resend it below."
                )
                return redirect("accounts:resend_verification")

            form.add_error(

                None,

                "Invalid Username/Email or Password."

            )

    else:

        form = UserLoginForm()

    context = {

        "form": form,

    }

    return render(

        request,

        "accounts/login.html",

        context

    )


# ==========================================================
# LOGOUT VIEW
# ==========================================================
#
# Logs the user out
# and redirects back
# to Login page.
#
def logout_view(request):

    logout(request)

    messages.success(request,"Logged out successfully.")

    return redirect(

        "accounts:login"

    )

# ==========================================================
# VERIFICATION PENDING VIEW
# ==========================================================
#
# Shown right after registration, telling the user to
# check their email before they can log in.
#
def verification_pending_view(request):

    return render(
        request,
        "accounts/verification_pending.html",
    )


# ==========================================================
# VERIFY EMAIL VIEW
# ==========================================================
#
# Handles the link the user clicks from their inbox.
# Decodes the uid, checks the token, and activates the
# account if everything is valid.
#
def verify_email_view(request, uidb64, token):

    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):

        user.is_active = True
        user.save(update_fields=["is_active"])

        messages.success(
            request,
            "Your email has been verified! You can now log in."
        )

        return redirect("accounts:login")

    return render(
        request,
        "accounts/verification_invalid.html",
    )


# ==========================================================
# RESEND VERIFICATION EMAIL VIEW
# ==========================================================
#
def resend_verification_view(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip()

        try:
            user = User.objects.get(email=email, is_active=False)
            send_verification_email(request, user)
            messages.success(
                request,
                "Verification email sent! Check your inbox."
            )
            return redirect("accounts:login")

        except User.DoesNotExist:
            messages.error(
                request,
                "No unverified account found with that email. "
                "It may already be verified, or the email may be incorrect."
            )

    return render(
        request,
        "accounts/resend_verification.html",
    )
