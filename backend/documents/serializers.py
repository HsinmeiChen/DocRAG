
from rest_framework import serializers
from django.conf import settings
from .models import Document

class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "title", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def validate_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        if value.size > settings.MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("PDF exceeds the upload size limit.")
        return value


class DocumentSerializer(serializers.ModelSerializer):
    chunks_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Document
        fields = ["id", "title", "uploaded_at", "index_status", "indexed_at", "chunks_count"]


class QuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000, allow_blank=False)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)
    score_threshold = serializers.FloatField(default=0.2, min_value=0, max_value=1)
    document_id = serializers.IntegerField(required=False, min_value=1)

    def validate_score_threshold(self, value):
        import math
        if not math.isfinite(value):
            raise serializers.ValidationError("Must be a finite number.")
        return value


class AskSerializer(QuerySerializer):
    score_threshold = serializers.FloatField(default=0.05, min_value=0, max_value=1)
