
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from inventory.models import UserProfile


class Command(BaseCommand):
    help = "Create the initial staff account."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_USER_USERNAME")
        email = os.getenv("DJANGO_USER_EMAIL")
        password = os.getenv("DJANGO_USER_PASSWORD")

        if not all([username, email, password]):
            raise CommandError(
                "Missing DJANGO_USER environment variables."
            )

        User = get_user_model()

        if User.objects.filter(username=username).exists():
            raise CommandError(
                f"Username '{username}' already exists."
            )

        validate_password(password)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        profile, created = UserProfile.objects.get_or_create(
            user=user
        )

        profile.role = "staff"
        profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Staff account '{username}' created successfully."
            )
        )
