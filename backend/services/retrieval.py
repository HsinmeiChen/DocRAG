from documents.models import Chunk
from services.embedding import embed_text
from services.qdrant_store import search_vectors


def retrieve_chunks(query, top_k, score_threshold, document_id=None):
    vector = embed_text(query)
    if not vector:
        raise ValueError("Embedding returned an empty vector.")
    hits = search_vectors(vector, top_k, score_threshold, document_id)
    chunks = Chunk.objects.filter(
        qdrant_point_id__in=[str(hit.id) for hit in hits], document__index_status="indexed")
    if document_id is not None:
        chunks = chunks.filter(document_id=document_id)
    by_id = {chunk.qdrant_point_id: chunk for chunk in chunks}
    return [(by_id[str(hit.id)], float(hit.score)) for hit in hits if str(hit.id) in by_id]
