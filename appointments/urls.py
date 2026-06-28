from django.urls import path

from .views import (
    AppointmentCancelView,
    AppointmentDetailView,
    AppointmentListCreateView,
    AppointmentPostponeView,
    AvailableSlotsView,
    DoctorListView,
)

urlpatterns = [
    path("", AppointmentListCreateView.as_view(), name="appointment-list"),
    path("<int:pk>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path(
        "<int:pk>/postpone/",
        AppointmentPostponeView.as_view(),
        name="appointment-postpone",
    ),
    path(
        "<int:pk>/cancel/",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path("available-slots/", AvailableSlotsView.as_view(), name="available-slots"),
    path("doctors/", DoctorListView.as_view(), name="doctor-list"),
]
