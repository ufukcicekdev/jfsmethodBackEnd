from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Appointment,
    AppointmentStatus,
    ClinicHoliday,
    ClinicScheduleSettings,
    WorkingDay,
)


def is_holiday(target_date) -> bool:
    return ClinicHoliday.objects.filter(date=target_date).exists()


def get_working_day(weekday: int) -> WorkingDay | None:
    return WorkingDay.objects.filter(day_of_week=weekday).first()


def generate_slot_starts(target_date):
    if is_holiday(target_date):
        return []

    working_day = get_working_day(target_date.weekday())
    if not working_day or not working_day.is_working:
        return []

    settings = ClinicScheduleSettings.get_solo()
    duration = timedelta(minutes=settings.slot_duration_minutes)
    start_dt = datetime.combine(target_date, working_day.start_time)
    end_dt = datetime.combine(target_date, working_day.end_time)

    slots = []
    current = start_dt
    while current + duration <= end_dt:
        slots.append(timezone.make_aware(current))
        current += duration

    return slots


def get_booked_counts(target_date):
    """Her (doctor_id, datetime) için aktif randevu sayısını döner."""
    counts = {}
    rows = Appointment.objects.filter(
        appointment_datetime__date=target_date,
        status__in=[AppointmentStatus.PENDING, AppointmentStatus.APPROVED],
    ).values_list("doctor_id", "appointment_datetime")
    for doctor_id, dt in rows:
        counts[(doctor_id, dt)] = counts.get((doctor_id, dt), 0) + 1
    return counts


def get_available_slots(target_date):
    doctors = User.objects.filter(is_staff=True, is_active=True)
    if not doctors.exists():
        return []

    slot_starts = generate_slot_starts(target_date)
    if not slot_starts:
        return []

    counts = get_booked_counts(target_date)
    capacity = ClinicScheduleSettings.get_solo().slot_capacity or 1
    now = timezone.now()
    slots = []

    for doctor in doctors:
        for slot_dt in slot_starts:
            if slot_dt <= now:
                continue
            booked = counts.get((doctor.id, slot_dt), 0)
            if booked >= capacity:
                continue
            slots.append(
                {
                    "datetime": slot_dt,
                    "doctor_id": doctor.id,
                    "doctor_name": doctor.get_full_name() or doctor.username,
                    "remaining": capacity - booked,
                }
            )

    return slots


def is_valid_appointment_slot(
    appointment_datetime, doctor_id: int, exclude_appointment_id: int | None = None
) -> bool:
    if appointment_datetime <= timezone.now():
        return False

    local_dt = timezone.localtime(appointment_datetime)
    target_date = local_dt.date()

    if is_holiday(target_date):
        return False

    working_day = get_working_day(target_date.weekday())
    if not working_day or not working_day.is_working:
        return False

    slot_time = local_dt.time()
    if slot_time < working_day.start_time or slot_time >= working_day.end_time:
        return False

    settings = ClinicScheduleSettings.get_solo()
    duration = timedelta(minutes=settings.slot_duration_minutes)
    start_dt = datetime.combine(target_date, working_day.start_time)
    end_dt = datetime.combine(target_date, working_day.end_time)
    current = start_dt

    valid_starts = []
    while current + duration <= end_dt:
        valid_starts.append(current.time())
        current += duration

    if slot_time not in valid_starts:
        return False

    booked_query = Appointment.objects.filter(
        doctor_id=doctor_id,
        appointment_datetime=appointment_datetime,
        status__in=[AppointmentStatus.PENDING, AppointmentStatus.APPROVED],
    )
    if exclude_appointment_id:
        booked_query = booked_query.exclude(pk=exclude_appointment_id)

    capacity = ClinicScheduleSettings.get_solo().slot_capacity or 1
    return booked_query.count() < capacity


def ensure_default_schedule():
    ClinicScheduleSettings.get_solo()
    defaults = {
        0: (True, "09:00", "18:00"),
        1: (True, "09:00", "18:00"),
        2: (True, "09:00", "18:00"),
        3: (True, "09:00", "18:00"),
        4: (True, "09:00", "18:00"),
        5: (False, "09:00", "13:00"),
        6: (False, "09:00", "13:00"),
    }
    for day, (is_working, start, end) in defaults.items():
        WorkingDay.objects.get_or_create(
            day_of_week=day,
            defaults={
                "is_working": is_working,
                "start_time": datetime.strptime(start, "%H:%M").time(),
                "end_time": datetime.strptime(end, "%H:%M").time(),
            },
        )
