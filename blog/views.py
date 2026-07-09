import os
import json
import re
import urllib.request
import urllib.error

from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff


def markdown_to_html(text: str) -> str:
    """Gemini'den gelen basit Markdown'ı Tiptap uyumlu HTML'e çevirir."""
    lines = text.split("\n")
    html_lines = []
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        if in_ol:
            html_lines.append("</ol>")
            in_ol = False

    ol_counter = [0]

    for line in lines:
        # Başlıklar
        if line.startswith("### "):
            close_lists()
            html_lines.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_lists()
            html_lines.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_lists()
            html_lines.append(f"<h1>{_inline(line[2:])}</h1>")
        # Unordered list
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul:
                close_lists()
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li><p>{_inline(line[2:])}</p></li>")
        # Ordered list
        elif re.match(r"^\d+\.\s", line):
            if not in_ol:
                close_lists()
                html_lines.append("<ol>")
                in_ol = True
            content = re.sub(r"^\d+\.\s", "", line)
            html_lines.append(f"<li><p>{_inline(content)}</p></li>")
        # Boş satır
        elif line.strip() == "":
            close_lists()
        # Normal paragraf
        else:
            close_lists()
            html_lines.append(f"<p>{_inline(line)}</p>")

    close_lists()
    return "\n".join(html_lines)


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text
from .models import BlogPost, BlogTopic
from .serializers import (
    BlogPostCreateSerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogTopicSerializer,
)


# ── Image upload ─────────────────────────────────────────────────────────────

class AdminBlogImageUploadView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response({"detail": "image alanı zorunlu."}, status=400)
        import uuid
        from django.core.files.storage import default_storage
        ext = image.name.rsplit(".", 1)[-1].lower()
        path = default_storage.save(f"blog/images/{uuid.uuid4().hex}.{ext}", image)
        url = request.build_absolute_uri(default_storage.url(path))
        return Response({"url": url}, status=201)


# ── Public endpoints ──────────────────────────────────────────────────────────

class PublicBlogListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        posts = BlogPost.objects.filter(is_published=True).order_by("-published_at")
        return Response(BlogPostListSerializer(posts, many=True, context={"request": request}).data)


class PublicBlogDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            post = BlogPost.objects.get(slug=slug, is_published=True)
        except BlogPost.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)
        post.view_count += 1
        post.save(update_fields=["view_count"])
        return Response(BlogPostDetailSerializer(post, context={"request": request}).data)


# ── Admin endpoints ───────────────────────────────────────────────────────────

class AdminBlogPostListView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        posts = BlogPost.objects.all()
        return Response(BlogPostListSerializer(posts, many=True, context={"request": request}).data)

    def post(self, request):
        ser = BlogPostCreateSerializer(data=request.data)
        if ser.is_valid():
            post = ser.save()
            return Response(BlogPostDetailSerializer(post, context={"request": request}).data, status=201)
        return Response(ser.errors, status=400)


class AdminBlogPostDetailView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _get(self, pk):
        try:
            return BlogPost.objects.get(pk=pk)
        except BlogPost.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self._get(pk)
        if not post:
            return Response({"detail": "Bulunamadı."}, status=404)
        return Response(BlogPostDetailSerializer(post, context={"request": request}).data)

    def patch(self, request, pk):
        post = self._get(pk)
        if not post:
            return Response({"detail": "Bulunamadı."}, status=404)
        ser = BlogPostDetailSerializer(post, data=request.data, partial=True, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(ser.data)
        return Response(ser.errors, status=400)

    def delete(self, request, pk):
        post = self._get(pk)
        if not post:
            return Response({"detail": "Bulunamadı."}, status=404)
        post.delete()
        return Response(status=204)


class AdminBlogTopicListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        topics = BlogTopic.objects.all()
        return Response(BlogTopicSerializer(topics, many=True).data)

    def post(self, request):
        ser = BlogTopicSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, status=201)
        return Response(ser.errors, status=400)


class AdminBlogTopicDetailView(APIView):
    permission_classes = [IsStaff]

    def delete(self, request, pk):
        try:
            BlogTopic.objects.get(pk=pk).delete()
        except BlogTopic.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)
        return Response(status=204)


class AdminBlogGenerateView(APIView):
    """Gemini API kullanarak belirtilen konu için blog yazısı üretir."""
    permission_classes = [IsStaff]

    def post(self, request):
        topic_id = request.data.get("topic_id")
        custom_topic = request.data.get("topic")

        topic_obj = None
        topic_text = custom_topic

        if topic_id:
            try:
                topic_obj = BlogTopic.objects.get(pk=topic_id)
                topic_text = topic_obj.topic
            except BlogTopic.DoesNotExist:
                return Response({"detail": "Konu bulunamadı."}, status=404)

        if not topic_text:
            return Response({"detail": "topic veya topic_id gerekli."}, status=400)

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return Response({"detail": "GEMINI_API_KEY tanımlı değil."}, status=500)

        prompt = (
            f"Sen deneyimli bir fizyoterapi ve sağlıklı yaşam uzmanısın. "
            f"Aşağıdaki konu hakkında Türkçe, SEO uyumlu, bilgilendirici ve akıcı bir blog yazısı yaz (en az 500 kelime).\n\n"
            f"SADECE aşağıdaki JSON formatında yanıt ver, başka hiçbir şey yazma:\n"
            f'{{"title": "Yazının başlığı", "content": "Yazının HTML içeriği"}}\n\n'
            f"content alanı geçerli HTML olsun: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em> etiketlerini kullan. "
            f"Markdown veya kod bloğu kullanma.\n\n"
            f"Konu: {topic_text}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return Response({"detail": f"Gemini API hatası: {body}"}, status=502)
        except Exception as e:
            return Response({"detail": str(e)}, status=502)

        try:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            title = parsed["title"]
            content = parsed["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return Response({"detail": f"Gemini yanıtı parse edilemedi: {e}"}, status=502)

        post = BlogPost.objects.create(
            title=title,
            content=content,
            is_published=True,
            ai_generated=True,
            topic=topic_obj,
            published_at=timezone.now(),
        )

        if topic_obj:
            topic_obj.is_generated = True
            topic_obj.save(update_fields=["is_generated"])

        return Response(BlogPostDetailSerializer(post, context={"request": request}).data, status=201)
