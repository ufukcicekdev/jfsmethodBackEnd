from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.patient_notification_views import (
    PatientNotificationListView,
    PatientNotificationMarkAllReadView,
    PatientNotificationMarkReadView,
)
from accounts.views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    FCMDeviceRegisterView,
    FCMDeviceUnregisterView,
    ForgotPasswordView,
    MeView,
    MyPackagesView,
    PatientProfileView,
    PublicPackagePlansView,
    RegisterView,
    ResetPasswordConfirmView,
    WeightHistoryListCreateView,
)
from accounts.site_views import (
    ContactMessageCreateView,
    PublicSiteSettingsView,
)
from accounts.admin_views import (
    PublicFaqListView,
    PatientDietPlanListView,
    PublicTestimonialListView,
    PublicLandingServiceView,
    PublicLandingTreatmentView,
    PublicLandingWhyUsView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "api/auth/change-password/",
        ChangePasswordView.as_view(),
        name="auth-change-password",
    ),
    path(
        "api/auth/forgot-password/",
        ForgotPasswordView.as_view(),
        name="auth-forgot-password",
    ),
    path(
        "api/auth/reset-password/",
        ResetPasswordConfirmView.as_view(),
        name="auth-reset-password",
    ),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/profile/", PatientProfileView.as_view(), name="patient-profile"),
    path(
        "api/weight-history/",
        WeightHistoryListCreateView.as_view(),
        name="weight-history",
    ),
    path(
        "api/devices/register/",
        FCMDeviceRegisterView.as_view(),
        name="fcm-device-register",
    ),
    path(
        "api/devices/unregister/",
        FCMDeviceUnregisterView.as_view(),
        name="fcm-device-unregister",
    ),
    path("api/packages/me/", MyPackagesView.as_view(), name="my-packages"),
    path(
        "api/package-plans/",
        PublicPackagePlansView.as_view(),
        name="public-package-plans",
    ),
    path(
        "api/notifications/",
        PatientNotificationListView.as_view(),
        name="patient-notifications",
    ),
    path(
        "api/notifications/read-all/",
        PatientNotificationMarkAllReadView.as_view(),
        name="patient-notifications-read-all",
    ),
    path(
        "api/notifications/<int:pk>/read/",
        PatientNotificationMarkReadView.as_view(),
        name="patient-notification-read",
    ),
    path(
        "api/site-settings/",
        PublicSiteSettingsView.as_view(),
        name="public-site-settings",
    ),
    path("api/contact/", ContactMessageCreateView.as_view(), name="contact-create"),
    path("api/faqs/", PublicFaqListView.as_view(), name="public-faqs"),
    path("api/my-diets/", PatientDietPlanListView.as_view(), name="patient-diets"),
    path("api/testimonials/", PublicTestimonialListView.as_view(), name="public-testimonials"),
    path("api/landing/services/", PublicLandingServiceView.as_view(), name="public-landing-services"),
    path("api/landing/treatments/", PublicLandingTreatmentView.as_view(), name="public-landing-treatments"),
    path("api/landing/why-us/", PublicLandingWhyUsView.as_view(), name="public-landing-why-us"),
    path("api/appointments/", include("appointments.urls")),
    path("api/wellness/", include("wellness.urls")),
    path("api/kvkk/", include("kvkk.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
