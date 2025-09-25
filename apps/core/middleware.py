import logging

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class UserIPMiddleware:
    """
    Middleware to track user's last login IP address and update user fields.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get user's IP address
        user_ip = self.get_client_ip(request)

        # Store IP in session for later use
        request.session["user_ip"] = user_ip

        response = self.get_response(request)

        # Update user's last_login_ip after successful authentication
        if hasattr(request, "user") and request.user.is_authenticated:
            try:
                user = request.user
                if user.last_login_ip != user_ip:
                    user.last_login_ip = user_ip
                    user.save(update_fields=["last_login_ip"])
            except Exception as e:
                logger.warning(f"Failed to update user's last_login_ip: {e}")

        return response

    def get_client_ip(self, request):
        """
        Get the client's real IP address, considering proxy headers.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("HTTP_X_REAL_IP") or request.META.get(
                "REMOTE_ADDR"
            )

        return ip
