from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from apps.core.models.base import Profile


class Command(BaseCommand):
    help = _("Generate default superuser(s)")

    def handle(self, *args, **kwargs):
        usernames = [
            {
                "username": "enlabe",
                "email": "enlabe@gmail.com",
                "bio": "Software developer",
                "avatar": "images/avatars/enlabe.png",
                "first_name": "Enlabe",
                "last_name": "Dev",
            }
        ]
        default_password = settings.USER_PASSWORD_DEFAULT

        if not default_password:
            self.stderr.write(
                _("Please add a default password in your .env file")
            )
            return

        User = get_user_model()
        created_users = []

        for username in usernames:
            user, created = User.objects.get_or_create(
                username=username["username"],
                defaults={
                    "email": username["email"],
                    "password": default_password,
                    "is_staff": True,
                    "is_superuser": True,
                    "first_name": username.get("first_name", ""),
                    "last_name": username.get("last_name", ""),
                },
            )
            if created:
                user.set_password(default_password)
                user.save()
                if "bio" in username or "avatar" in username:
                    profile, __ = Profile.objects.get_or_create(user=user)
                    profile.bio = username.get("bio", "")
                    if "avatar" in username:
                        profile.avatar = username["avatar"]
                    profile.save()

                    created_users.append(username["username"])

        if created_users:
            self.stdout.write(
                self.style.SUCCESS(
                    _(
                        "Created the following users: %(users)s with password: %(password)s"
                    )
                    % {
                        "users": ", ".join(created_users),
                        "password": default_password,
                    }
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    _("No new users were created. They already exist.")
                )
            )
