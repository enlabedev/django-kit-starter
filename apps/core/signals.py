import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(user_logged_in)
def update_user_last_login_fields(sender, user, request, **kwargs):
    """
    Signal handler to update user fields on successful login.
    """
    try:
        user_ip = getattr(request.session, "user_ip", None)
        if user_ip:
            user.last_login_ip = user_ip
            user.save(update_fields=["last_login_ip"])

        logger.info(
            _("Updated login fields for user: %(username)s")
            % {"username": user.username}
        )
    except Exception as e:
        logger.error(
            _("Error updating user login fields: %(error)s") % {"error": e}
        )


@receiver(post_save, sender=User)
def update_password_change_timestamp(sender, instance, created, **kwargs):
    """
    Signal handler to update last_password_change_at when password is changed.
    """
    if not created and instance.pk:
        try:
            old_user = User.objects.get(pk=instance.pk)
            if old_user.password != instance.password:
                User.objects.filter(pk=instance.pk).update(
                    last_password_change_at=timezone.now()
                )
                logger.info(
                    _(
                        "Password change timestamp updated for user: %(username)s"
                    )
                    % {"username": instance.username}
                )
        except User.DoesNotExist:
            pass


@receiver(pre_save, sender=User)
def reset_password_change_required(sender, instance, **kwargs):
    """
    Signal handler to reset password_change_required when password is changed.
    """
    if not instance.pk:
        return

    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    if old_instance.password != instance.password:
        User.objects.filter(pk=instance.pk).update(
            password_change_required=False
        )
        logger.info(
            _("Password change required reset for user: %(username)s")
            % {"username": instance.username}
        )
