from django.contrib import admin

from .models import (
    AdminNotification,
    Appointment,
    ClinicHoliday,
    ClinicScheduleSettings,
    DayCancellation,
    WorkingDay,
)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "patient",
        "doctor",
        "appointment_datetime",
        "status",
        "created_at",
    ]
    list_filter = ["status", "appointment_datetime"]
    search_fields = [
        "patient__username",
        "doctor__username",
        "note",
    ]
    raw_id_fields = ["patient", "doctor"]
    date_hierarchy = "appointment_datetime"


@admin.register(ClinicScheduleSettings)
class ClinicScheduleSettingsAdmin(admin.ModelAdmin):
    list_display = ["slot_duration_minutes"]


@admin.register(WorkingDay)
class WorkingDayAdmin(admin.ModelAdmin):
    list_display = ["day_of_week", "is_working", "start_time", "end_time"]
    list_editable = ["is_working", "start_time", "end_time"]


@admin.register(ClinicHoliday)
class ClinicHolidayAdmin(admin.ModelAdmin):
    list_display = ["date", "name", "created_at"]
    list_filter = ["date"]
    search_fields = ["name"]


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "notification_type", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["title", "message"]
    raw_id_fields = ["appointment", "actor"]


@admin.register(DayCancellation)
class DayCancellationAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "appointments_cancelled",
        "emails_sent",
        "cancelled_by",
        "created_at",
    ]
    list_filter = ["date", "created_at"]
    search_fields = ["reason"]
    raw_id_fields = ["cancelled_by"]
