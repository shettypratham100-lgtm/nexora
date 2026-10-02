from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin.models import LogEntry

from .views import send_verification_email

User = get_user_model()


class NexoraUserAdmin(DjangoUserAdmin):

    list_display = (
        "username", "email", "first_name", "last_name",
        "is_verified", "is_staff", "date_joined",
    )

    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    @admin.display(boolean=True, description="Verified")
    def is_verified(self, user):
        # is_active doubles as "email verified" in Nexora --
        # see apps/accounts/forms.py UserRegistrationForm.save()
        return user.is_active

    actions = [
        "force_verify_accounts",
        "resend_verification_emails",
        "activate_accounts",
        "deactivate_accounts",
        "make_staff",
        "remove_staff",
    ]

    @admin.action(description="Activate selected accounts")
    def activate_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self._log(request, f"Activated {updated} account(s)")
        self.message_user(request, f"{updated} account(s) activated.")

    @admin.action(description="Deactivate selected accounts")
    def deactivate_accounts(self, request, queryset):
        # Prevent an admin from locking themselves out
        queryset = queryset.exclude(pk=request.user.pk)
        updated = queryset.update(is_active=False)
        self._log(request, f"Deactivated {updated} account(s)")
        self.message_user(request, f"{updated} account(s) deactivated.")

    @admin.action(description="Grant staff access")
    def make_staff(self, request, queryset):
        # Superuser promotion is intentionally NOT exposed here --
        # staff status is safe to bulk-grant, superuser is not.
        updated = queryset.update(is_staff=True)
        self._log(request, f"Granted staff access to {updated} account(s)")
        self.message_user(request, f"{updated} account(s) granted staff access.")

    @admin.action(description="Revoke staff access")
    def remove_staff(self, request, queryset):
        queryset = queryset.exclude(pk=request.user.pk)
        updated = queryset.update(is_staff=False, is_superuser=False)
        self._log(request, f"Revoked staff access from {updated} account(s)")
        self.message_user(request, f"{updated} account(s) had staff access revoked.")

    def _log(self, request, message):
        from django.contrib.admin.models import LogEntry, CHANGE
        from django.contrib.contenttypes.models import ContentType
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(User).pk,
            object_id="",
            object_repr="Bulk user action",
            action_flag=CHANGE,
            change_message=message,
        )
    

    @admin.action(description="Force-verify selected accounts")
    def force_verify_accounts(self, request, queryset):
        updated = queryset.update(is_active=True)
        self._log(request, f"Force-verified {updated} account(s)")
        self.message_user(request, f"{updated} account(s) verified.")

    @admin.action(description="Resend verification email to selected (unverified only)")
    def resend_verification_emails(self, request, queryset):
        unverified = queryset.filter(is_active=False)
        for user in unverified:
            send_verification_email(request, user)
        self._log(request, f"Resent verification emails to {unverified.count()} account(s)")
        self.message_user(request, f"Verification email resent to {unverified.count()} account(s).")


admin.site.unregister(User)
admin.site.register(User, NexoraUserAdmin)



@admin.register(LogEntry)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = ("action_time", "user", "content_type", "object_repr", "action_flag_display", "change_message")
    list_filter = ("action_flag", "content_type", "action_time")
    search_fields = ("object_repr", "change_message", "user__username")
    date_hierarchy = "action_time"

    @admin.display(description="Action")
    def action_flag_display(self, entry):
        return {1: "Added", 2: "Changed", 3: "Deleted"}.get(entry.action_flag, "Unknown")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False