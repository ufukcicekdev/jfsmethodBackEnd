"""
Planlanmış blog konularını Gemini API ile üretir.
Cronjob: her gün çalıştır, tarih gelen konuları işler.
  python manage.py generate_scheduled_blogs
"""
import json
import os
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import BlogPost, BlogTopic


class Command(BaseCommand):
    help = "Scheduled blog topics generate via Gemini API"

    def handle(self, *args, **options):
        today = timezone.now().date()
        topics = BlogTopic.objects.filter(scheduled_date__lte=today, is_generated=False)

        if not topics.exists():
            self.stdout.write("Bugün için bekleyen konu yok.")
            return

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            self.stderr.write("GEMINI_API_KEY tanımlı değil.")
            return

        for topic_obj in topics:
            self.stdout.write(f"Üretiliyor: {topic_obj.topic}")
            prompt = (
                f"Sen deneyimli bir fizyoterapi ve sağlıklı yaşam uzmanısın. "
                f"Aşağıdaki konu hakkında Türkçe, SEO uyumlu, bilgilendirici ve akıcı bir blog yazısı yaz (en az 500 kelime).\n\n"
                f"SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:\n"
                f'{{"title": "Yazının başlığı", "content": "Yazının HTML içeriği"}}\n\n'
                f"content alanı geçerli HTML olsun: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em> etiketlerini kullan. "
                f"Markdown veya kod bloğu kullanma.\n\n"
                f"Konu: {topic_obj.topic}"
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read())
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                title = parsed["title"]
                content = parsed["content"]
            except Exception as e:
                self.stderr.write(f"Hata ({topic_obj.topic}): {e}")
                continue

            BlogPost.objects.create(
                title=title,
                content=content,
                is_published=True,
                ai_generated=True,
                topic=topic_obj,
                published_at=timezone.now(),
            )
            topic_obj.is_generated = True
            topic_obj.save(update_fields=["is_generated"])
            self.stdout.write(self.style.SUCCESS(f"  ✓ {title}"))
