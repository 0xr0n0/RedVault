"""
Management command to create an initial admin user if none exist.

Generates a random secure password on first run and prints it to stdout.

Usage:
    python manage.py seed_admin
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


def generate_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # Ensure at least one of each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    # Shuffle so the guaranteed chars aren't always at the start
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


class Command(BaseCommand):
    help = "Create a default admin user if no admin exists."

    def handle(self, *args, **options):
        if User.objects.filter(role="admin").exists():
            self.stdout.write(self.style.WARNING("An admin user already exists. Skipping."))
            return

        password = generate_password()

        admin = User.objects.create_superuser(
            username="admin",
            email="admin@redteam.local",
            password=password,
            first_name="System",
            last_name="Admin",
            role="admin",
        )

        self.stdout.write(self.style.SUCCESS(
            "\n"
            "╔══════════════════════════════════════════╗\n"
            "║       ADMIN USER CREATED                 ║\n"
            "╠══════════════════════════════════════════╣\n"
            f"║  Username: {admin.username:<29}║\n"
            f"║  Password: {password:<29}║\n"
            "╠══════════════════════════════════════════╣\n"
            "║  ⚠️  Save this password now!              ║\n"
            "║  It will NOT be shown again.             ║\n"
            "╚══════════════════════════════════════════╝\n"
        ))
