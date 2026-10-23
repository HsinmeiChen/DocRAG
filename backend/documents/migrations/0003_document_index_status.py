from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_chunk")]
    operations = [
        migrations.AddField(model_name="document", name="index_status",
            field=models.CharField(max_length=16, default="uploaded", choices=[
                ("uploaded", "Uploaded"), ("indexing", "Indexing"),
                ("indexed", "Indexed"), ("failed", "Failed")])),
        migrations.AddField(model_name="document", name="indexed_at",
            field=models.DateTimeField(null=True, blank=True)),
        migrations.AddConstraint(model_name="chunk", constraint=models.UniqueConstraint(
            fields=("document", "page", "chunk_index"), name="unique_chunk_position")),
        migrations.AddIndex(model_name="chunk",
            index=models.Index(fields=["qdrant_point_id"], name="chunk_point_idx")),
    ]
