# ==========================================================
# IMPORTS
# ==========================================================

# Django function used to define URL routes
from django.urls import path

# Import all views from the current app
from . import views

from django.contrib.auth import views as auth_views
from .forms import NexoraPasswordResetForm, NexoraSetPasswordForm

# ==========================================================
# APP NAME
# ==========================================================
#
# app_name creates a URL namespace.
#
# Instead of writing:
#
#     {% url 'login' %}
#
# we write:
#
#     {% url 'accounts:login' %}
#
# This prevents conflicts if another app
# also has a URL named "login".
#
app_name = "accounts"


# ==========================================================
# URL PATTERNS
# ==========================================================
#
# Every page related to authentication
# is registered here.
#
urlpatterns = [

    # ------------------------------------------------------
    # LOGIN
    # ------------------------------------------------------
    #
    # URL:
    #
    # /accounts/login/
    #
    # Displays the login page and
    # authenticates the user.
    #
    path(
        "login/",
        views.login_view,
        name="login"
    ),

    # ------------------------------------------------------
    # REGISTER
    # ------------------------------------------------------
    #
    # URL:
    #
    # /accounts/register/
    #
    # Allows a new user to create
    # a Nexora account.
    #
    path(
        "register/",
        views.register_view,
        name="register"
    ),

    # ------------------------------------------------------
    # LOGOUT
    # ------------------------------------------------------
    #
    # URL:
    #
    # /accounts/logout/
    #
    # Logs the current user out
    # and redirects to Login.
    #
    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

        # ------------------------------------------------------
    # FORGOT PASSWORD (4-step flow, handled by Django's
    # built-in auth views — token generation/validation is
    # done securely by Django itself)
    # ------------------------------------------------------

    # Step 1: user enters their email
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            form_class=NexoraPasswordResetForm,
            success_url="/accounts/password-reset/done/",
        ),
        name="password_reset",
    ),

    # Step 2: "check your email" confirmation page
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    # Step 3: user clicks the emailed link, sets a new password
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=NexoraSetPasswordForm,
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm",
    ),

    # Step 4: "password changed" success page
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # ------------------------------------------------------
    # EMAIL VERIFICATION (required before login works)
    # ------------------------------------------------------

    path(
        "verification-pending/",
        views.verification_pending_view,
        name="verification_pending",
    ),

    path(
        "verify/<uidb64>/<token>/",
        views.verify_email_view,
        name="verify_email",
    ),

    path(
        "resend-verification/",
        views.resend_verification_view,
        name="resend_verification",
    ),
]

