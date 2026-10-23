from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Chunk, Document


class AskViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.document = Document.objects.create(
            title="測試手冊",
            file="uploads/test.pdf",
            index_status="indexed",
        )
        self.first_chunk = Chunk.objects.create(
            document=self.document,
            page=2,
            chunk_index=0,
            content="請假規定內容",
            qdrant_point_id="point-1",
        )
        self.second_chunk = Chunk.objects.create(
            document=self.document,
            page=3,
            chunk_index=0,
            content="出差規定內容",
            qdrant_point_id="point-2",
        )

    @patch("documents.views.answer_with_context")
    @patch("documents.views.retrieve_chunks")
    def test_returns_only_citations_used_with_chinese_brackets(
        self,
        mock_retrieve_chunks,
        mock_answer_with_context,
    ):
        mock_retrieve_chunks.return_value = [
            (self.first_chunk, 0.91),
            (self.second_chunk, 0.72),
        ]
        mock_answer_with_context.return_value = "請假規定如下【1】。"

        response = self.client.post(
            "/api/ask/",
            {
                "query": "請假規定是什麼？",
                "document_id": self.document.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["citations"]), 1)
        self.assertEqual(response.data["citations"][0]["citation_id"], 1)
        self.assertEqual(
            response.data["citations"][0]["chunk_index"],
            self.first_chunk.chunk_index,
        )

    @patch("documents.views.answer_with_context")
    @patch("documents.views.retrieve_chunks")
    def test_returns_no_citations_when_answer_uses_none(
        self,
        mock_retrieve_chunks,
        mock_answer_with_context,
    ):
        mock_retrieve_chunks.return_value = [
            (self.first_chunk, 0.31),
            (self.second_chunk, 0.25),
        ]
        mock_answer_with_context.return_value = (
            "提供的上下文中沒有關於交通補助的資訊。"
        )

        response = self.client.post(
            "/api/ask/",
            {
                "query": "交通補助每月多少元？",
                "document_id": self.document.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["citations"], [])