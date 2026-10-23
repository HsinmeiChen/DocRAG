from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection

def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
        return JsonResponse({"status": "ok", "db": row[0]})
    except Exception:
        return JsonResponse({"status": "unavailable", "db": None}, status=503)

def home(request):
    return JsonResponse({"message": "API is running. Try /health/ or /api/."})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include("documents.urls")),
    path("", home),
]
