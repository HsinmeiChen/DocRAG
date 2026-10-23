from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    index_status = models.CharField(max_length=16, default="uploaded", choices=[
        ("uploaded", "Uploaded"), ("indexing", "Indexing"),
        ("indexed", "Indexed"), ("failed", "Failed")])
    indexed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title or self.file.name
    
class Chunk(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    page = models.IntegerField()
    chunk_index = models.IntegerField()
    content = models.TextField()
    qdrant_point_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["document", "page", "chunk_index"], name="unique_chunk_position")]
        indexes = [models.Index(fields=["qdrant_point_id"], name="chunk_point_idx")]

    def __str__(self):
        return f"Doc {self.document.id} - Page {self.page} - Chunk {self.chunk_index}"
