from rest_framework import serializers

from .models import ContactMessage, LandingService, LandingTreatment, LandingWhyUsItem, SiteSettings, Testimonial

_CONTACT_FIELDS = [
    "clinic_name",
    "address",
    "phone",
    "whatsapp",
    "email",
    "working_hours",
    "map_embed_url",
    "instagram_url",
    "facebook_url",
    "x_url",
    "youtube_url",
    "linkedin_url",
    "google_analytics_id",
    "google_search_console_verification",
    "registration_enabled",
    "section_stats",
    "section_marquee",
    "section_about",
    "section_services",
    "section_digital_twin",
    "section_treatments",
    "section_how_it_works",
    "section_why_us",
    "section_testimonials",
    "section_packages",
    "section_cta",
    "section_faq",
    "expert_visible",
    "expert_name",
    "expert_title",
    "expert_bio",
    "expert_years",
    "expert_patient_count",
    "expert_rating",
    "expert_badges",
]


class PublicSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = _CONTACT_FIELDS


class AdminSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [*_CONTACT_FIELDS, "updated_at"]
        read_only_fields = ["updated_at"]


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]

    def validate(self, attrs):
        if not (attrs.get("email") or attrs.get("phone")):
            raise serializers.ValidationError(
                "Lütfen e-posta veya telefon bilgisinden en az birini girin."
            )
        return attrs


class AdminContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "is_read",
            "created_at",
        ]


class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = ["id", "name", "treatment", "text", "rating", "is_active", "sort_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class LandingServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingService
        fields = ["id", "icon", "tag", "title", "description", "sort_order", "is_active"]


class LandingTreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingTreatment
        fields = ["id", "title", "description", "sort_order", "is_active"]


class LandingWhyUsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingWhyUsItem
        fields = ["id", "icon", "title", "description", "sort_order", "is_active"]
