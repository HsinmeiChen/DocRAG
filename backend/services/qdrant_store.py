from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
)


def get_client():
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=30)

def ensure_collection(vector_size):
    client = get_client()
    collection = settings.QDRANT_COLLECTION

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

    info = client.get_collection(collection)
    config = info.config.params.vectors

    if not isinstance(config, VectorParams) or config.size != vector_size:
        raise ValueError(
            "Collection vector dimensions do not match the embedding model."
        )

    if "document_id" not in info.payload_schema:
        client.create_payload_index(
            collection_name=collection,
            field_name="document_id",
            field_schema=PayloadSchemaType.INTEGER,
            wait=True,
        )

def upsert_vectors(items):
    get_client().upsert(collection_name=settings.QDRANT_COLLECTION,
        points=[PointStruct(id=pid, vector=vector, payload=payload) for pid, vector, payload in items],
        wait=True)


def search_vectors(vector, top_k, score_threshold, document_id=None):
    client = get_client()
    if not client.collection_exists(settings.QDRANT_COLLECTION):
        return []
    query_filter = None
    if document_id is not None:
        query_filter = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
    return client.query_points(collection_name=settings.QDRANT_COLLECTION, query=vector,
        limit=top_k, score_threshold=score_threshold, query_filter=query_filter).points
