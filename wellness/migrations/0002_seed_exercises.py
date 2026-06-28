from django.db import migrations


DEFAULT_EXERCISES = [
    {
        "title": "Boyun Esnetme",
        "description": "Boyun ve üst sırt gerginliğini azaltır.",
        "instructions": (
            "1. Dik oturun, omuzları gevşetin.\n"
            "2. Başı yavaşça sağa eğin, 15 saniye tutun.\n"
            "3. Merkeze dönün, sola tekrarlayın.\n"
            "4. Her yönde 3 tekrar yapın."
        ),
        "target_region": "neck",
        "duration_minutes": 5,
        "sets": 3,
        "reps": 3,
        "difficulty": "easy",
    },
    {
        "title": "Omuz Dairesel Hareket",
        "description": "Omuz eklemi mobilitesini artırır.",
        "instructions": (
            "1. Ayakta durun, kollar yanlarda.\n"
            "2. Omuzları yavaşça yukarı, geri, aşağı daire çizin.\n"
            "3. 10 daire ileri, 10 daire geri.\n"
            "4. Ağrı hissederseniz durun."
        ),
        "target_region": "shoulder_left",
        "duration_minutes": 5,
        "sets": 2,
        "reps": 10,
        "difficulty": "easy",
    },
    {
        "title": "Kedi-Deve (Cat-Cow)",
        "description": "Bel ve omurga esnekliğini destekler.",
        "instructions": (
            "1. Dört ayak üzerinde durun.\n"
            "2. Nefes alırken sırtı çukurlaştırın (deve).\n"
            "3. Nefes verirken sırtı yuvarlayın (kedi).\n"
            "4. 10 yavaş tekrar yapın."
        ),
        "target_region": "lower_back",
        "duration_minutes": 8,
        "sets": 2,
        "reps": 10,
        "difficulty": "easy",
    },
    {
        "title": "Pelvik Tilt",
        "description": "Bel kaslarını güçlendirir ve destekler.",
        "instructions": (
            "1. Sırtüstü yatın, dizler bükülü.\n"
            "2. Bel boşluğunu yavaşça yere bastırın.\n"
            "3. 5 saniye tutun, gevşetin.\n"
            "4. 12 tekrar yapın."
        ),
        "target_region": "lower_back",
        "duration_minutes": 8,
        "sets": 3,
        "reps": 12,
        "difficulty": "medium",
    },
    {
        "title": "Düz Bacak Kaldırma",
        "description": "Kalça ve karın kaslarını güçlendirir.",
        "instructions": (
            "1. Sırtüstü yatın, bir bacak düz.\n"
            "2. Diğer bacağı 45° kaldırın, 3 saniye tutun.\n"
            "3. Yavaşça indirin.\n"
            "4. Her bacak için 10 tekrar."
        ),
        "target_region": "hip_left",
        "duration_minutes": 10,
        "sets": 3,
        "reps": 10,
        "difficulty": "medium",
    },
    {
        "title": "Duvar Kayması",
        "description": "Omuz bıçakları arası güçlendirme.",
        "instructions": (
            "1. Sırtınız duvara, dirsekler 90°.\n"
            "2. Kolları yukarı kaydırın, omuzları duvara yakın tutun.\n"
            "3. Yavaşça başlangıca dönün.\n"
            "4. 10 tekrar yapın."
        ),
        "target_region": "upper_back",
        "duration_minutes": 7,
        "sets": 3,
        "reps": 10,
        "difficulty": "easy",
    },
    {
        "title": "Diz Fleksiyonu (Oturarak)",
        "description": "Diz eklemi hareketliliğini korur.",
        "instructions": (
            "1. Sandalyede dik oturun.\n"
            "2. Bacağı yavaşça kaldırın, diz tam açılana kadar.\n"
            "3. 3 saniye tutun, indirin.\n"
            "4. Her bacak 12 tekrar."
        ),
        "target_region": "knee_left",
        "duration_minutes": 8,
        "sets": 3,
        "reps": 12,
        "difficulty": "easy",
    },
    {
        "title": "Thoracic Rotation",
        "description": "Göğüs kafesi rotasyonu, postür için önemli.",
        "instructions": (
            "1. Yan yatın, dizler bükülü.\n"
            "2. Üst kolu karşı tarafa açarak döndürün.\n"
            "3. 5 saniye tutun.\n"
            "4. Her taraf 8 tekrar."
        ),
        "target_region": "upper_back",
        "duration_minutes": 10,
        "sets": 2,
        "reps": 8,
        "difficulty": "medium",
    },
]


def seed_exercises(apps, schema_editor):
    Exercise = apps.get_model("wellness", "Exercise")
    for item in DEFAULT_EXERCISES:
        Exercise.objects.get_or_create(title=item["title"], defaults=item)


def unseed_exercises(apps, schema_editor):
    Exercise = apps.get_model("wellness", "Exercise")
    titles = [item["title"] for item in DEFAULT_EXERCISES]
    Exercise.objects.filter(title__in=titles).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("wellness", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_exercises, unseed_exercises),
    ]
