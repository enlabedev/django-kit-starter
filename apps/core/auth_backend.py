import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomModelBackend(ModelBackend):
    """
    Custom authentication backend that handles failed login attempts
    and account locking functionality.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None

        if self._is_account_locked(user):
            logger.warning(f"Login attempt for locked account: {username}")
            return None

        if user.check_password(password):
            self._handle_successful_login(user, request)
            return user

        self._handle_failed_login(user, request)
        return None

    def _is_account_locked(self, user):
        """
        Check if the user account is currently locked.
        """
        if not user.locked_until:
            return False

        if timezone.now() > user.locked_until:
            user.locked_until = None
            user.failed_login_attempts = 0
            user.save(update_fields=["locked_until", "failed_login_attempts"])
            return False

        return True

    def _handle_successful_login(self, user, request):
        """
        Handle successful login: reset failed attempts, update last login IP.
        """
        user.failed_login_attempts = 0
        user.locked_until = None
        user_ip = getattr(request.session, "user_ip", None)
        if user_ip:
            user.last_login_ip = user_ip

        user.save(
            update_fields=[
                "failed_login_attempts",
                "locked_until",
                "last_login_ip",
            ]
        )
        logger.info(f"Successful login for user: {user.username}")

    def _handle_failed_login(self, user, request):
        """
        Handle failed login: increment attempts, lock account if necessary.
        """
        user.failed_login_attempts += 1
        max_attempts = 3

        if user.failed_login_attempts >= max_attempts:
            lock_duration = timedelta(minutes=15)
            user.locked_until = timezone.now() + lock_duration
            logger.warning(f"Account locked for user: {user.username}")

        user.save(update_fields=["failed_login_attempts", "locked_until"])
        logger.warning(
            f"Failed login attempt for user: {user.username} (attempts: {user.failed_login_attempts})"
        )

    def get_user(self, user_id):
        """
        Get user by ID.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
