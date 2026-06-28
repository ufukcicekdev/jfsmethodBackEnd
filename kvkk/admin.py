from django.contrib import admin

from .models import KVKKConsentLog


@admin.register(KVKKConsentLog)
class KVKKConsentLogAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "user",
        "consent_type",
        "is_accepted",
        "kvkk_version",
        "ip_address",
    ]
    list_filter = ["consent_type", "is_accepted", "kvkk_version", "timestamp"]
    search_fields = ["user__username", "user__email", "ip_address"]
    readonly_fields = [
        "user",
        "consent_type",
        "is_accepted",
        "kvkk_version",
        "ip_address",
        "user_agent",
        "timestamp",
    ]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
