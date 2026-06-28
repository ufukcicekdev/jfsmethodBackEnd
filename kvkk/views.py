from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CookieConsentSerializer
from .services import log_consents


class CookieConsentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CookieConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        log_consents(request, serializer.to_consent_items(), user=user)

        return Response(
            {"detail": "Çerez tercihleri kaydedildi."},
            status=status.HTTP_201_CREATED,
        )
