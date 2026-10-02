# ==========================================================
# IMPORTS
# ==========================================================

# Django's built-in User model.
#
# We use Django's authentication system instead
# of creating our own user table because it is
# secure, well-tested and follows industry standards.
#
from django.contrib.auth.models import User


# Django's built-in registration form.
#
# This form already provides:
#
# • Password Hashing
# • Password Confirmation
# • Password Strength Validation
#
# We extend it instead of writing everything ourselves.
#
from django.contrib.auth.forms import UserCreationForm


# Django Forms Module.
#
# Used to create HTML forms and perform
# automatic validation.
#
from django import forms


# ValidationError allows us to display
# custom validation messages.
#
from django.core.exceptions import ValidationError


# ==========================================================
# USER REGISTRATION FORM
# ==========================================================
#
# This form is responsible for creating
# a new Nexora account.
#
# Instead of creating everything from scratch,
# we inherit Django's UserCreationForm and
# customize it according to our requirements.
#
class UserRegistrationForm(UserCreationForm):

    # ------------------------------------------------------
    # EMAIL FIELD
    # ------------------------------------------------------
    #
    # Django's default UserCreationForm
    # does not include Email.
    #
    # Nexora requires Email because it will
    # later support:
    #
    # • Forgot Password
    # • Password Reset Emails
    # • Email Notifications
    # • OTP Verification (Future)
    #
    email = forms.EmailField(

        required=True,

        label="Email Address",

        help_text="",

        widget=forms.EmailInput(

            attrs={

                "class": "form-control",

                "placeholder": "Enter your email"

            }

        )

    )


    # ------------------------------------------------------
    # META CLASS
    # ------------------------------------------------------
    #
    # Meta tells Django:
    #
    # 1. Which database model this form uses.
    #
    # 2. Which fields should appear on
    #    the Registration page.
    #
    class Meta:

        model = User

        fields = [
            "first_name",

            "last_name",

            "username",

            "email",

            "password1",

            "password2",

        ]

        widgets = {

            "username": forms.TextInput(

                attrs={

                    "class": "form-control",

                    "placeholder": "Choose a username"

                }

            ),

        }
    # ------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------
    #
    # This method runs automatically
    # whenever the form is created.
    #
    # We use it to customize
    # Django's default password fields.
    #

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["first_name"].widget.attrs.update({

            "class": "form-control",

            "placeholder": "Enter your first name"

        })

        self.fields["last_name"].widget.attrs.update({

            "class": "form-control",

            "placeholder": "Enter your last name"

        })

        self.fields["password1"].widget.attrs.update({

            "class": "form-control",

            "placeholder": "Create a password"

        })

        self.fields["password2"].widget.attrs.update({

            "class": "form-control",

            "placeholder": "Confirm your password"

        })

        self.fields["username"].help_text = ""

        self.fields["password1"].help_text = ""

        self.fields["password2"].help_text = ""

    # ------------------------------------------------------
    # EMAIL VALIDATION
    # ------------------------------------------------------
    #
    # Django automatically calls this method
    # when:
    #
    # form.is_valid()
    #
    # is executed.
    #
    # Purpose:
    #
    # Prevent two accounts from using
    # the same email address.
    #
    def clean_email(self):

        email = self.cleaned_data.get("email")

        if User.objects.filter(email=email).exists():

            raise ValidationError(

                "An account with this email already exists."

            )

        return email


    # ------------------------------------------------------
    # SAVE USER
    # ------------------------------------------------------
    #
    # UserCreationForm already creates
    # Username and Password.
    #
    # Since we added Email,
    # we must save it ourselves.
    #
    def save(self, commit=True):

        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        # ------------------------------------------------------
        # Account starts INACTIVE until the user clicks the
        # verification link emailed to them. Django's built-in
        # authenticate() already refuses inactive users, so this
        # alone blocks login until verification is complete.
        # ------------------------------------------------------
        user.is_active = False

        if commit:

            user.save()

        return user
    

# ==========================================================
# USER LOGIN FORM
# ==========================================================
#
# Django's default AuthenticationForm only
# accepts Username.
#
# Nexora allows users to login using:
#
# • Username
# • Email
#
# Therefore we create our own login form.
#
class UserLoginForm(forms.Form):

    # ------------------------------------------------------
    # USERNAME OR EMAIL
    # ------------------------------------------------------

    username_or_email = forms.CharField(

        label="",

        widget=forms.TextInput(

            attrs={

                "class": "form-control",

                "placeholder": "Username or Email"

            }

        )

    )

    # ------------------------------------------------------
    # PASSWORD
    # ------------------------------------------------------

    password = forms.CharField(

        label="",

        widget=forms.PasswordInput(

            attrs={

                "class": "form-control",

                "placeholder": "Password"

            }

        )

    )

    # ------------------------------------------------------
# FIRST NAME
# ------------------------------------------------------

first_name = forms.CharField(

    required=True,

    label="First Name",

    widget=forms.TextInput(

        attrs={

            "class": "form-control",

            "placeholder": "Enter your first name"

        }

    )

)


# ------------------------------------------------------
# LAST NAME
# ------------------------------------------------------

last_name = forms.CharField(

    required=True,

    label="Last Name",

    widget=forms.TextInput(

        attrs={

            "class": "form-control",

            "placeholder": "Enter your last name"

        }

    )

)

# ==========================================================
# PASSWORD RESET FORM (email-existence check)
# ==========================================================
#
# Django's built-in PasswordResetForm always shows the same
# "check your email" success message whether the email exists
# or not -- a deliberate security measure to stop attackers
# from using the form to discover which emails have accounts.
#
# Nexora explicitly wants the opposite: tell the user clearly
# if the email isn't registered. This is a conscious trade-off
# (it does make email enumeration possible) accepted here for
# a clearer user experience on a student project.
#
from django.contrib.auth.forms import PasswordResetForm


class NexoraPasswordResetForm(PasswordResetForm):

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if not User.objects.filter(email=email).exists():

            raise ValidationError(
                "This email is not registered with Nexora."
            )

        return email


# ==========================================================
# SET NEW PASSWORD FORM (styled)
# ==========================================================
#
# Django's built-in SetPasswordForm renders plain, unstyled
# inputs (no "form-control" class), which is why the reset
# page looked broken/native. This subclass just adds the same
# Bootstrap styling every other form field in the app uses.
#
from django.contrib.auth.forms import SetPasswordForm


class NexoraSetPasswordForm(SetPasswordForm):

    new_password1 = forms.CharField(
        label="New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter new password",
            "autocomplete": "new-password",
        }),
    )

    new_password2 = forms.CharField(
        label="Confirm New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm new password",
            "autocomplete": "new-password",
        }),
    )
