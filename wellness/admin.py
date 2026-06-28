from django.contrib import admin

from .models import (
    Exercise,
    ExerciseAssignment,
    ExerciseCompletion,
    RegionPainLog,
)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["title", "target_region", "difficulty", "is_active"]
    list_filter = ["difficulty", "target_region", "is_active"]
    search_fields = ["title", "description"]


@admin.register(RegionPainLog)
class RegionPainLogAdmin(admin.ModelAdmin):
    list_display = ["patient", "region", "pain_level", "recorded_at"]
    list_filter = ["region", "recorded_at"]
    raw_id_fields = ["patient"]


@admin.register(ExerciseAssignment)
class ExerciseAssignmentAdmin(admin.ModelAdmin):
    list_display = ["patient", "exercise", "frequency", "is_active", "created_at"]
    list_filter = ["is_active", "frequency"]
    raw_id_fields = ["patient", "exercise", "assigned_by"]


@admin.register(ExerciseCompletion)
class ExerciseCompletionAdmin(admin.ModelAdmin):
    list_display = ["patient", "assignment", "completed_at"]
    raw_id_fields = ["patient", "assignment"]
