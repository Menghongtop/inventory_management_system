
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


class Command(BaseCommand):
    help = "Create the initial production superuser."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            raise CommandError(
                "Set DJANGO_SUPERUSER_USERNAME, "
                "DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD."
            )

        User = get_user_model()

        existing_user = User.objects.filter(
            username=username
        ).first()

        if existing_user:
            if existing_user.is_superuser:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Production superuser already exists."
                    )
                )
                return

            raise CommandError(
                "This username already exists but is not a superuser."
            )

        validate_password(password)

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Production superuser '{username}' created successfully."
            )
        )
