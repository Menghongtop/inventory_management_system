
import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from inventory.models import UserProfile


class Command(BaseCommand):
    help = "Create the initial staff account if it does not exist."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_USER_USERNAME")
        email = os.getenv("DJANGO_USER_EMAIL")
        password = os.getenv("DJANGO_USER_PASSWORD")

        if not all([username, email, password]):
            raise CommandError(
                "Missing DJANGO_USER environment variables."
            )

        User = get_user_model()

        user = User.objects.filter(username=username).first()

        if user:
            self.stdout.write(
                self.style.WARNING(
                    f"User '{username}' already exists. "
                    "Keeping the existing account and password."
                )
            )
        else:
            validate_password(password)

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Staff account '{username}' created successfully."
                )
            )

        profile, created = UserProfile.objects.get_or_create(
            user=user
        )

        if profile.role != "staff":
            profile.role = "staff"
            profile.save(update_fields=["role"])

        if created:
            self.stdout.write("Staff profile created successfully.")
