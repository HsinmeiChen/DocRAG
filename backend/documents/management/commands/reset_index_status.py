from django.core.management.base import BaseCommand, CommandError
from documents.models import Document


class Command(BaseCommand):
    help = "Recover an indexing status after a stopped worker. Stop active indexing requests first."

    def add_arguments(self, parser):
        parser.add_argument("document_id", type=int)

    def handle(self, *args, **options):
        count = Document.objects.filter(id=options["document_id"], index_status="indexing").update(
            index_status="failed", indexed_at=None)
        if not count:
            raise CommandError("Document does not exist or is not indexing.")
        self.stdout.write(self.style.SUCCESS("Status reset to failed. Retry the index endpoint."))
