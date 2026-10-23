from pypdf import PdfReader

def chunk_pdf(file_path, chunk_size=100):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    reader = PdfReader(file_path)
    chunks = []

    for page_number, page in enumerate(reader.pages):
        text = page.extract_text() or ""

        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]

            if chunk_text.strip():  
                chunks.append({
                    "page": page_number + 1,
                    "chunk_index": i // chunk_size,
                    "content": chunk_text
                })

    return chunks
