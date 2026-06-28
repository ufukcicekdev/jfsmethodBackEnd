from datetime import timedelta

from django.utils import timezone

from .models import WeightHistory


def get_weight_stats(patient_id: int) -> dict:
    entries = list(
        WeightHistory.objects.filter(patient_id=patient_id)
        .order_by("recorded_at")
        .values("weight", "recorded_at")
    )

    if not entries:
        return {
            "current_weight": None,
            "weight_change_week": None,
            "weight_change_month": None,
            "history": [],
        }

    current = entries[-1]
    now = timezone.now()

    def reference_at(days: int):
        cutoff = now - timedelta(days=days)
        candidate = None
        for entry in entries:
            if entry["recorded_at"] <= cutoff:
                candidate = entry
            else:
                break
        return candidate

    week_ref = reference_at(7)
    month_ref = reference_at(30)

    def change(ref):
        if not ref:
            return None
        return round(current["weight"] - ref["weight"], 1)

    return {
        "current_weight": current["weight"],
        "weight_change_week": change(week_ref),
        "weight_change_month": change(month_ref),
        "history": [
            {
                "weight": entry["weight"],
                "recorded_at": entry["recorded_at"].isoformat(),
            }
            for entry in entries[-90:]
        ],
    }
