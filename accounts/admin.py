from django.contrib import admin

from .models import (
    ContactMessage,
    FCMDevice,
    PackagePlan,
    PatientProfile,
    PatientProgressPhoto,
    PostureAssessment,
    SessionPackage,
    SiteSettings,
    WeightHistory,
)


@admin.register(PostureAssessment)
class PostureAssessmentAdmin(admin.ModelAdmin):
    list_display = ["patient", "view", "created_by", "created_at"]
    list_filter = ["view", "created_at"]
    search_fields = ["patient__username"]
    raw_id_fields = ["patient", "created_by"]
    readonly_fields = ["metrics", "created_at"]


@admin.register(PackagePlan)
class PackagePlanAdmin(admin.ModelAdmin):
    list_display = ["name", "total_sessions", "price", "is_active", "sort_order"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    list_editable = ["sort_order", "is_active"]


@admin.register(SessionPackage)
class SessionPackageAdmin(admin.ModelAdmin):
    list_display = [
        "patient",
        "name",
        "total_sessions",
        "price",
        "is_paid",
        "purchased_at",
        "is_active",
    ]
    list_filter = ["is_active", "is_paid", "purchased_at"]
    search_fields = ["patient__username", "name"]
    raw_id_fields = ["patient", "plan", "created_by"]


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "is_active", "user_agent", "updated_at"]
    list_filter = ["is_active", "updated_at"]
    search_fields = ["user__username", "token"]
    raw_id_fields = ["user"]


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "height", "weight", "phone", "updated_at"]
    search_fields = ["user__username", "user__email"]
    raw_id_fields = ["user"]


@admin.register(WeightHistory)
class WeightHistoryAdmin(admin.ModelAdmin):
    list_display = ["patient", "weight", "recorded_at"]
    list_filter = ["recorded_at"]
    search_fields = ["patient__username"]
    raw_id_fields = ["patient"]


@admin.register(PatientProgressPhoto)
class PatientProgressPhotoAdmin(admin.ModelAdmin):
    list_display = ["patient", "category", "title", "taken_at", "created_at"]
    list_filter = ["category", "created_at"]
    search_fields = ["patient__username", "title", "note"]
    raw_id_fields = ["patient", "uploaded_by"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            "İletişim Bilgileri",
            {
                "fields": (
                    "clinic_name",
                    "address",
                    "phone",
                    "whatsapp",
                    "email",
                    "working_hours",
                    "map_embed_url",
                )
            },
        ),
        (
            "Sosyal Medya",
            {
                "fields": (
                    "instagram_url",
                    "facebook_url",
                    "x_url",
                    "youtube_url",
                    "linkedin_url",
                )
            },
        ),
        (
            "SEO / Analytics",
            {
                "fields": (
                    "google_analytics_id",
                    "google_search_console_verification",
                ),
                "description": (
                    "Google Analytics ölçüm kimliği (G-...) ve Google Search "
                    "Console HTML etiketi doğrulama içeriği."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "email", "phone", "is_read", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["name", "email", "phone", "subject", "message"]
    readonly_fields = ["name", "email", "phone", "subject", "message", "created_at"]
