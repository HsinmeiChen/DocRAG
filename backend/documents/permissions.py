import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class ProjectAPIAccess(BasePermission):
    """Optional shared demo key; production settings require it."""
    message = "A valid X-API-Key header is required."

    def has_permission(self, request, view):
        expected = settings.PROJECT_API_KEY
        return not expected or secrets.compare_digest(
            request.headers.get("X-API-Key", ""), expected)
