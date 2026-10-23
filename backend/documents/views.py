import logging
import uuid
import re

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pypdf.errors import PdfReadError
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Chunk
from .serializers import DocumentUploadSerializer, DocumentSerializer, QuerySerializer, AskSerializer
from services.pdf_chunker import chunk_pdf
from services.embedding import embed_text
from services.qdrant_store import ensure_collection, upsert_vectors
from services.retrieval import retrieve_chunks
from services.llm import answer_with_context

logger = logging.getLogger(__name__)


def generate_chunk_id(chunk_id):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"enterprise-qa/chunks/{chunk_id}"))


def upstream_error(operation):
    logger.exception("External service failed during %s", operation)
    return Response({"error": "upstream_unavailable", "message": "External service unavailable. Retry later."},
        status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DocumentUploadView(generics.ListAPIView):
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DocumentSerializer
    queryset = Document.objects.annotate(chunks_count=Count("chunks")).order_by("-uploaded_at", "-id")

    def post(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = serializer.validated_data["file"]
        try:
            chunks = chunk_pdf(uploaded, chunk_size=500)
        except (PdfReadError, ValueError, OSError):
            return Response({"file": "Invalid or unreadable PDF."}, status=400)
        if not chunks:
            return Response({"file": "PDF has no extractable text. OCR is not supported."}, status=400)
        uploaded.seek(0)
        doc = None
        try:
            with transaction.atomic():
                doc = serializer.save()
                Chunk.objects.bulk_create([Chunk(document=doc, **chunk) for chunk in chunks])
        except Exception:
            if doc is not None:
                doc.file.delete(save=False)
            raise
        return Response({"id": doc.id, "title": doc.title, "file": doc.file.url,
            "chunks_created": len(chunks), "index_status": doc.index_status}, status=status.HTTP_201_CREATED)


class DocumentDetailView(generics.RetrieveAPIView):
    serializer_class = DocumentSerializer
    queryset = Document.objects.annotate(chunks_count=Count("chunks"))
    lookup_url_kwarg = "doc_id"


class DocumentIndexView(APIView):
    def post(self, request, doc_id, *args, **kwargs):
        doc = get_object_or_404(Document, id=doc_id)
        chunks = list(doc.chunks.order_by("page", "chunk_index"))
        if not chunks:
            return Response({"error": "No chunks found for this document."}, status=400)
        # Atomic claim prevents two requests from indexing the same document.
        claimed = Document.objects.filter(id=doc_id).exclude(index_status="indexing").update(
            index_status="indexing", indexed_at=None)
        if not claimed:
            return Response({"error": "Document is already being indexed."}, status=409)
        try:
            items = []
            for chunk in chunks:
                vector = embed_text(chunk.content)
                if not vector:
                    raise ValueError("Chunk embedding is empty.")
                point_id = generate_chunk_id(chunk.pk)
                items.append((point_id, vector, {"document_id": doc_id,
                    "page": chunk.page, "chunk_index": chunk.chunk_index}))
                chunk.qdrant_point_id = point_id
            ensure_collection(len(items[0][1]))
            upsert_vectors(items)
            # Local IDs are committed only after Qdrant acknowledges the write.
            # A DB failure can be retried with the same deterministic point IDs.
            with transaction.atomic():
                Chunk.objects.bulk_update(chunks, ["qdrant_point_id"])
                Document.objects.filter(id=doc_id).update(index_status="indexed", indexed_at=timezone.now())
        except Exception:
            Document.objects.filter(id=doc_id).update(index_status="failed")
            return upstream_error("document indexing")
        return Response({"document_id": doc_id, "indexed": len(items), "skipped_empty": 0,
            "index_status": "indexed", "collection": settings.QDRANT_COLLECTION})


class SearchView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = QuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        try:
            retrieved = retrieve_chunks(**params)
        except Exception:
            return upstream_error("search")
        return Response({**params, "results": [{"score": score, "document_id": chunk.document_id,
            "page": chunk.page, "chunk_index": chunk.chunk_index, "content": chunk.content,
            "qdrant_point_id": chunk.qdrant_point_id} for chunk, score in retrieved]})


class AskView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        try:
            retrieved = retrieve_chunks(**params)
            if not retrieved:
                return Response({"query": params["query"], "answer": "No relevant chunks found.", "citations": []})
            context = "\n\n".join(f"[{i}] Doc {chunk.document_id}, p.{chunk.page}\n{chunk.content}"
                for i, (chunk, _) in enumerate(retrieved, 1))
            answer = answer_with_context(params["query"], context)
            normalized_answer = answer.replace("【", "[").replace("】", "]")
            cited_ids = {
                int(match)
                for match in re.findall(r"\[(\d+)\]", normalized_answer)
            }
        except Exception:
            return upstream_error("question answering")
        return Response({"query": params["query"], "answer": answer,
            "citations": [{"citation_id": i, "document_id": chunk.document_id, "page": chunk.page,
                "chunk_index": chunk.chunk_index, "score": score}
                for i, (chunk, score) in enumerate(retrieved, 1) if i in cited_ids]})
