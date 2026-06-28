from django.urls import path

from .admin_views import (
    AdminAppointmentListView,
    AdminAppointmentStatusView,
    AdminAttendanceView,
    AdminTestimonialListView,
    AdminTestimonialDetailView,
    AdminLandingServiceListView,
    AdminLandingServiceDetailView,
    AdminLandingTreatmentListView,
    AdminLandingTreatmentDetailView,
    AdminLandingWhyUsListView,
    AdminLandingWhyUsDetailView,
    AdminBodyMeasurementDetailView,
    AdminBodyMeasurementListCreateView,
    AdminDashboardView,
    AdminDietItemDetailView,
    AdminDietItemListView,
    AdminFaqDetailView,
    AdminFaqListView,
    AdminPackagePlanDetailView,
    AdminPackagePlanListCreateView,
    AdminPatientDetailView,
    AdminPatientDietPlanDetailView,
    AdminPatientDietPlanListView,
    AdminPatientListView,
    AdminPatientPackageDetailView,
    AdminPatientPackageListCreateView,
    AdminPatientPhotoDeleteView,
    AdminPatientPhotoListCreateView,
    AdminPatientPostureDeleteView,
    AdminPatientPostureListCreateView,
    AdminPatientWeightView,
)

from appointments.schedule_views import (
    AdminCancelDayPreviewView,
    AdminCancelDayView,
    AdminHolidayDeleteView,
    AdminHolidayListCreateView,
    AdminScheduleView,
)

from appointments.notification_views import (
    AdminNotificationListView,
    AdminNotificationMarkAllReadView,
    AdminNotificationMarkReadView,
)

from .site_views import (
    AdminContactMessageDetailView,
    AdminContactMessageListView,
    AdminSiteSettingsView,
)

from wellness.urls import admin_urlpatterns as wellness_admin_urls

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("patients/", AdminPatientListView.as_view(), name="admin-patients"),
    path(
        "patients/<int:pk>/",
        AdminPatientDetailView.as_view(),
        name="admin-patient-detail",
    ),
    path(
        "patients/<int:pk>/weight/",
        AdminPatientWeightView.as_view(),
        name="admin-patient-weight",
    ),
    path(
        "patients/<int:pk>/photos/",
        AdminPatientPhotoListCreateView.as_view(),
        name="admin-patient-photos",
    ),
    path(
        "patients/<int:pk>/photos/<int:photo_id>/",
        AdminPatientPhotoDeleteView.as_view(),
        name="admin-patient-photo-delete",
    ),
    path(
        "patients/<int:pk>/posture/",
        AdminPatientPostureListCreateView.as_view(),
        name="admin-patient-posture",
    ),
    path(
        "patients/<int:pk>/posture/<int:assessment_id>/",
        AdminPatientPostureDeleteView.as_view(),
        name="admin-patient-posture-delete",
    ),
    path(
        "patients/<int:pk>/packages/",
        AdminPatientPackageListCreateView.as_view(),
        name="admin-patient-packages",
    ),
    path(
        "patients/<int:pk>/packages/<int:package_id>/",
        AdminPatientPackageDetailView.as_view(),
        name="admin-patient-package-detail",
    ),
    path(
        "patients/<int:patient_id>/measurements/",
        AdminBodyMeasurementListCreateView.as_view(),
        name="admin-body-measurements",
    ),
    path(
        "patients/<int:patient_id>/measurements/<int:measurement_id>/",
        AdminBodyMeasurementDetailView.as_view(),
        name="admin-body-measurement-detail",
    ),
    path(
        "appointments/",
        AdminAppointmentListView.as_view(),
        name="admin-appointments",
    ),
    path(
        "appointments/<int:pk>/status/",
        AdminAppointmentStatusView.as_view(),
        name="admin-appointment-status",
    ),
    path("schedule/", AdminScheduleView.as_view(), name="admin-schedule"),
    path(
        "schedule/holidays/",
        AdminHolidayListCreateView.as_view(),
        name="admin-schedule-holidays",
    ),
    path(
        "schedule/holidays/<int:pk>/",
        AdminHolidayDeleteView.as_view(),
        name="admin-schedule-holiday-delete",
    ),
    path(
        "schedule/cancel-day/preview/",
        AdminCancelDayPreviewView.as_view(),
        name="admin-cancel-day-preview",
    ),
    path(
        "schedule/cancel-day/",
        AdminCancelDayView.as_view(),
        name="admin-cancel-day",
    ),
    path(
        "notifications/",
        AdminNotificationListView.as_view(),
        name="admin-notifications",
    ),
    path(
        "notifications/read-all/",
        AdminNotificationMarkAllReadView.as_view(),
        name="admin-notifications-read-all",
    ),
    path(
        "notifications/<int:pk>/read/",
        AdminNotificationMarkReadView.as_view(),
        name="admin-notification-read",
    ),
    path(
        "package-plans/",
        AdminPackagePlanListCreateView.as_view(),
        name="admin-package-plans",
    ),
    path(
        "package-plans/<int:plan_id>/",
        AdminPackagePlanDetailView.as_view(),
        name="admin-package-plan-detail",
    ),
    path(
        "site-settings/",
        AdminSiteSettingsView.as_view(),
        name="admin-site-settings",
    ),
    path(
        "contact-messages/",
        AdminContactMessageListView.as_view(),
        name="admin-contact-messages",
    ),
    path(
        "contact-messages/<int:pk>/",
        AdminContactMessageDetailView.as_view(),
        name="admin-contact-message-detail",
    ),
    path("faqs/", AdminFaqListView.as_view(), name="admin-faqs"),
    path("faqs/<int:faq_id>/", AdminFaqDetailView.as_view(), name="admin-faq-detail"),
    path("diet-items/", AdminDietItemListView.as_view(), name="admin-diet-items"),
    path("diet-items/<int:pk>/", AdminDietItemDetailView.as_view(), name="admin-diet-item-detail"),
    path("patients/<int:patient_id>/diets/", AdminPatientDietPlanListView.as_view(), name="admin-patient-diets"),
    path("patients/<int:patient_id>/diets/<int:plan_id>/", AdminPatientDietPlanDetailView.as_view(), name="admin-patient-diet-detail"),
    path("patients/<int:patient_id>/attendance/", AdminAttendanceView.as_view(), name="admin-patient-attendance"),
    path("testimonials/", AdminTestimonialListView.as_view(), name="admin-testimonials"),
    path("testimonials/<int:pk>/", AdminTestimonialDetailView.as_view(), name="admin-testimonial-detail"),
    path("landing/services/", AdminLandingServiceListView.as_view(), name="admin-landing-services"),
    path("landing/services/<int:pk>/", AdminLandingServiceDetailView.as_view(), name="admin-landing-service-detail"),
    path("landing/treatments/", AdminLandingTreatmentListView.as_view(), name="admin-landing-treatments"),
    path("landing/treatments/<int:pk>/", AdminLandingTreatmentDetailView.as_view(), name="admin-landing-treatment-detail"),
    path("landing/why-us/", AdminLandingWhyUsListView.as_view(), name="admin-landing-why-us"),
    path("landing/why-us/<int:pk>/", AdminLandingWhyUsDetailView.as_view(), name="admin-landing-why-us-detail"),
    *wellness_admin_urls,
]
