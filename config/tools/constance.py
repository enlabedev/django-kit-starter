from django.utils.translation import gettext_lazy as _

CONSTANCE_CONFIG = {
    "USER_PASSWORD_DEFAULT": (
        "Ee147852",
        _("Default password for new users"),
    )
}
CONSTANCE_CONFIG_FIELDSETS = {
    "General": ("USER_PASSWORD_DEFAULT",),
}
