from django.urls import path

from .admin_views import (
    AdminPatientWellnessHistoryView,
    AdminCategoryTreeView,
    AdminCategoryDetailView,
    AdminExerciseDetailView,
    AdminExerciseListView,
    AdminPatientExerciseDeactivateView,
    AdminPatientExerciseListCreateView,
    NotificationScheduleDetailView,
    NotificationScheduleListCreateView,
    NotificationScheduleTestView,
    AdminExerciseProgramListView,
    AdminExerciseProgramDetailView,
    AdminProgramDayListView,
    AdminProgramDayDetailView,
    AdminProgramItemListView,
    AdminProgramItemDetailView,
    AdminProductPackageListView,
    AdminProductPackageDetailView,
    AdminPackageAssignmentListView,
    AdminPackageAssignmentDetailView,
    AdminPatientMealLogListView,
    AdminUserNotifScheduleListView,
    AdminUserNotifScheduleDetailView,
    AdminPatientProgramLogView,
)
from .views import (
    CompleteExerciseView,
    DailyStepView,
    DailyWaterView,
    PainMapView,
    PatientExerciseListView,
    PatientMealLogListView,
    PatientMealLogDetailView,
    PatientProgramView,
    PatientLogExerciseView,
    PatientProgressPhotoDeleteView,
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
    path(
        "progress-photos/<int:pk>/",
        PatientProgressPhotoDeleteView.as_view(),
        name="wellness-progress-photo-delete",
    ),
    path("water/", DailyWaterView.as_view(), name="wellness-water"),
    path("steps/", DailyStepView.as_view(), name="wellness-steps"),
    path("meal-logs/", PatientMealLogListView.as_view(), name="wellness-meal-logs"),
    path("meal-logs/<int:pk>/", PatientMealLogDetailView.as_view(), name="wellness-meal-log-detail"),
    path("my-program/", PatientProgramView.as_view(), name="wellness-my-program"),
    path("my-program/items/<int:item_id>/complete/", PatientLogExerciseView.as_view(), name="wellness-log-exercise"),
]

admin_urlpatterns = [
    path("categories/", AdminCategoryTreeView.as_view(), name="admin-categories"),
    path("categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    path("exercises/", AdminExerciseListView.as_view(), name="admin-exercises"),
    path(
        "patients/<int:pk>/wellness-history/",
        AdminPatientWellnessHistoryView.as_view(),
        name="admin-patient-wellness-history",
    ),
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
    # Exercise Programs
    path("exercise-programs/", AdminExerciseProgramListView.as_view(), name="admin-exercise-programs"),
    path("exercise-programs/<int:pk>/", AdminExerciseProgramDetailView.as_view(), name="admin-exercise-program-detail"),
    path("exercise-programs/<int:program_pk>/days/", AdminProgramDayListView.as_view(), name="admin-program-days"),
    path("program-days/<int:pk>/", AdminProgramDayDetailView.as_view(), name="admin-program-day-detail"),
    path("program-days/<int:day_pk>/items/", AdminProgramItemListView.as_view(), name="admin-program-items"),
    path("program-items/<int:pk>/", AdminProgramItemDetailView.as_view(), name="admin-program-item-detail"),
    # Patient tracking (admin view)
    path("patients/<int:patient_id>/meal-logs/", AdminPatientMealLogListView.as_view(), name="admin-patient-meal-logs"),
    path("patients/<int:patient_id>/meal-logs/<int:log_id>/", AdminPatientMealLogListView.as_view(), name="admin-patient-meal-log-note"),
    path("patients/<int:patient_id>/program-logs/", AdminPatientProgramLogView.as_view(), name="admin-patient-program-logs"),
    path("patients/<int:patient_id>/notification-schedules/", AdminUserNotifScheduleListView.as_view(), name="admin-patient-notif-schedules"),
    path("patients/<int:patient_id>/notification-schedules/<int:pk>/", AdminUserNotifScheduleDetailView.as_view(), name="admin-patient-notif-schedule-detail"),
    # Product Packages
    path("packages/", AdminProductPackageListView.as_view(), name="admin-packages"),
    path("packages/<int:pk>/", AdminProductPackageDetailView.as_view(), name="admin-package-detail"),
    path("package-assignments/", AdminPackageAssignmentListView.as_view(), name="admin-package-assignments"),
    path("package-assignments/<int:pk>/", AdminPackageAssignmentDetailView.as_view(), name="admin-package-assignment-detail"),
]
