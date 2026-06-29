from django.urls import path

from .admin_views import (
    AdminExerciseDetailView,
    AdminExerciseListView,
    AdminPatientExerciseDeactivateView,
    AdminPatientExerciseListCreateView,
    NotificationScheduleDetailView,
    NotificationScheduleListCreateView,
    NotificationScheduleTestView,
)
from .views import (
    CompleteExerciseView,
    DailyStepView,
    DailyWaterView,
    PainMapView,
    PatientExerciseListView,
    PatientProgressPhotoListView,
    WellnessDashboardView,
)

urlpatterns = [
    path("dashboard/", WellnessDashboardView.as_view(), name="wellness-dashboard"),
    path("pain-map/", PainMapView.as_view(), name="wellness-pain-map"),
    path("exercises/", PatientExerciseListView.as_view(), name="wellness-exercises"),
    path(
        "exercises/<int:pk>/complete/",
        CompleteExerciseView.as_view(),
        name="wellness-exercise-complete",
    ),
    path(
        "progress-photos/",
        PatientProgressPhotoListView.as_view(),
        name="wellness-progress-photos",
    ),
    path("water/", DailyWaterView.as_view(), name="wellness-water"),
    path("steps/", DailyStepView.as_view(), name="wellness-steps"),
]

admin_urlpatterns = [
    path("exercises/", AdminExerciseListView.as_view(), name="admin-exercises"),
    path(
        "exercises/<int:exercise_id>/",
        AdminExerciseDetailView.as_view(),
        name="admin-exercise-detail",
    ),
    path(
        "patients/<int:pk>/exercises/",
        AdminPatientExerciseListCreateView.as_view(),
        name="admin-patient-exercises",
    ),
    path(
        "patients/<int:pk>/exercises/<int:assignment_id>/",
        AdminPatientExerciseDeactivateView.as_view(),
        name="admin-patient-exercise-deactivate",
    ),
    path(
        "notification-schedules/",
        NotificationScheduleListCreateView.as_view(),
        name="admin-notification-schedules",
    ),
    path(
        "notification-schedules/<int:pk>/",
        NotificationScheduleDetailView.as_view(),
        name="admin-notification-schedule-detail",
    ),
    path(
        "notification-schedules/<int:pk>/test/",
        NotificationScheduleTestView.as_view(),
        name="admin-notification-schedule-test",
    ),
]
