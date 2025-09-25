import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def update_user_last_login_fields(sender, user, request, **kwargs):
    """
    Signal handler to update user fields on successful login.
    """
    try:
        # Get IP from session (set by middleware)
        user_ip = getattr(request.session, "user_ip", None)
        if user_ip:
            user.last_login_ip = user_ip
            user.save(update_fields=["last_login_ip"])

        logger.info(f"Updated login fields for user: {user.username}")
    except Exception as e:
        logger.error(f"Error updating user login fields: {e}")


@receiver(post_save)
def update_password_change_timestamp(sender, instance, created, **kwargs):
    """
    Signal handler to update last_password_change_at when password is changed.
    """
    # Only process User model instances
    if sender.__name__ != "User":
        return

    User = get_user_model()
    if not created and instance.pk:
        # Check if password was changed
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.password != instance.password:
                instance.last_password_change_at = timezone.now()
                instance.save(update_fields=["last_password_change_at"])
                logger.info(
                    f"Password change timestamp updated for user: {instance.username}"
                )
        except User.DoesNotExist:
            pass


@receiver(post_save)
def reset_password_change_required(sender, instance, created, **kwargs):
    """
    Signal handler to reset password_change_required when password is changed.
    """
    # Only process User model instances
    if sender.__name__ != "User":
        return

    User = get_user_model()
    if not created and instance.pk:
        # Check if password was changed
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.password != instance.password:
                instance.password_change_required = False
                instance.save(update_fields=["password_change_required"])
                logger.info(
                    f"Password change required reset for user: {instance.username}"
                )
        except User.DoesNotExist:
            pass
