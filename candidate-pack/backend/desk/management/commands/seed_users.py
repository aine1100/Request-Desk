import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from desk.models import User


class Command(BaseCommand):
    help = "Create or update the seed accounts. Passwords are stored hashed."

    def add_arguments(self, parser):
        parser.add_argument("--path", default="")

    def handle(self, *args, **options):
        path = self._resolve_path(options["path"])
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload:
            email = entry["email"].strip().lower()
            user, _created = User.objects.get_or_create(
                email=email,
                defaults={
                    "name": entry["name"],
                    "role": entry["role"],
                    "organisation": entry.get("organisation", ""),
                },
            )
            user.name = entry["name"]
            user.role = entry["role"]
            user.organisation = entry.get("organisation", "")
            user.is_active = True
            user.is_staff = entry["role"] == "admin"
            user.is_superuser = entry["role"] == "admin"
            user.set_password(entry["password"])
            user.save()
            self.stdout.write(f"seeded {email} ({user.role})")

    def _resolve_path(self, explicit):
        if explicit:
            return Path(explicit)
        if settings.SEED_USERS_PATH:
            return Path(settings.SEED_USERS_PATH)
        env_path = os.environ.get("SEED_USERS_PATH", "")
        if env_path:
            return Path(env_path)
        return Path(settings.BASE_DIR).parent / "seed" / "users.json"
