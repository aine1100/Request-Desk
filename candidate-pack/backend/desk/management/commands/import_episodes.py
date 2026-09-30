import json
from pathlib import Path

from django.core.management.base import BaseCommand

from desk.services.importing import import_csv_text


class Command(BaseCommand):
    help = "Import episode metadata from a CSV export."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        text = Path(options["path"]).read_text(encoding="utf-8-sig")
        report = import_csv_text(text)
        self.stdout.write(json.dumps(report, indent=2))
