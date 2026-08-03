from PIL import Image
import io
from django.core.files.base import ContentFile

MAX_DIM = 1920
QUALITY = 85


def convert_to_webp(image_field):
    """Convert an ImageField file to WebP in-place. Call in model.save() before super()."""
    if not image_field or not image_field.name:
        return
    if image_field.name.lower().endswith('.webp'):
        return  # already webp
    try:
        img = Image.open(image_field)
        img = img.convert("RGBA" if img.mode in ("RGBA", "LA") else "RGB")
        # Resize if too large
        w, h = img.size
        if max(w, h) > MAX_DIM:
            ratio = MAX_DIM / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=QUALITY, method=6)
        buf.seek(0)
        # Change filename to .webp
        base = image_field.name.rsplit('.', 1)[0]
        new_name = f"{base}.webp"
        image_field.save(new_name, ContentFile(buf.read()), save=False)
    except Exception:
        pass  # don't break upload if conversion fails
