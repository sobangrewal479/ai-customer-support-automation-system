from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from knowledge.models import KnowledgeDocument
from knowledge.services import (
    DocumentIndexingError,
    index_document,
)


class Command(BaseCommand):
    help = (
        "Extract and index an active knowledge PDF "
        "using its database ID."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "document_id",
            type=int,
            help="Database ID of the knowledge document.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]

        try:
            document = KnowledgeDocument.objects.get(
                pk=document_id
            )
        except KnowledgeDocument.DoesNotExist as error:
            raise CommandError(
                f"Knowledge document {document_id} "
                "does not exist."
            ) from error

        self.stdout.write(
            f"Indexing: {document.title} "
            f"(version {document.version})"
        )

        try:
            chunk_count = index_document(document)
        except DocumentIndexingError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed document {document_id} "
                f"into {chunk_count} searchable chunks."
            )
        )