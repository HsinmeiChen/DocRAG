from django.conf import settings
from openai import OpenAI


def get_client():
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=2)


def embed_text(text: str) -> list[float]:
    text = (text or "").strip()
    if not text:
        return []
    response = get_client().embeddings.create(model=settings.OPENAI_EMBEDDING_MODEL, input=text)
    return response.data[0].embedding
