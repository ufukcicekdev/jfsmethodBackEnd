from rest_framework import permissions


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        )


def HasSection(section):
    """IsStaff + belirli bir panel bölümüne erişim yetkisi kontrolü.

    Kullanım:
        permission_classes = [HasSection("ogrenciler")]

    Kurallar:
      - Superuser her bölüme erişir.
      - AdminProfile'i olmayan staff kullanıcı kısıtlanmaz (geriye dönük uyumluluk).
      - allowed_sections boşsa kısıtlama yoktur (tüm bölümler).
      - Aksi halde yalnızca allowed_sections içindeki bölümlere erişilir.
    """

    class _HasSection(permissions.BasePermission):
        required_section = section

        def has_permission(self, request, view):
            user = request.user
            if not (user.is_authenticated and (user.is_staff or user.is_superuser)):
                return False
            if user.is_superuser:
                return True
            profile = getattr(user, "admin_profile", None)
            if profile is None:
                return True
            return profile.has_section(section)

    _HasSection.__name__ = "HasSection_" + section.replace("-", "_")
    return _HasSection
