import uuid
from datetime import datetime
from typing import Any

import openpyxl
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)

from .models.base import User
from .services import bulk_block, bulk_restore, bulk_soft_delete, bulk_unblock

admin.site.unregister(Group)


class MixinActionAdmin(SimpleHistoryAdmin, ModelAdmin):
    """
    A mixin providing common actions like Excel export and row-level action buttons.
    """

    actions = ["export_excel"]

    @action(description=_("Export to Excel"), url_path="export-excel")
    def export_excel(
        self, request: HttpRequest, queryset: QuerySet
    ) -> HttpResponse:
        """Export selected records to an Excel file."""
        wb = openpyxl.Workbook()
        ws = wb.active
        model = queryset.model
        ws.title = f"{model._meta.verbose_name_plural}"

        headers = [field.name for field in model._meta.fields]
        ws.append(headers)

        for obj in queryset:
            row = []
            for field in model._meta.fields:
                value = getattr(obj, field.name)
                if isinstance(value, uuid.UUID):
                    value = str(value)
                # Excel does not support timezone-aware datetimes, so make them naive.
                elif isinstance(value, datetime) and value.tzinfo:
                    value = value.astimezone().replace(tzinfo=None)
                elif isinstance(value, Model):
                    value = str(value)
                row.append(value)
            ws.append(row)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f"attachment; filename={model._meta.model_name}_export.xlsx"
        )
        wb.save(response)
        return response

    @admin.display(description=_("Actions"))
    def action_buttons(self, obj: Any) -> str:
        """Render custom action buttons for each row."""
        if not obj.pk:
            return "-"

        opts = obj._meta
        change_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]
        )
        delete_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_delete", args=[obj.pk]
        )
        # Recommendation: Use CSS classes from the admin theme instead of inline styles.
        # Example: class="button button--primary", class="button button--danger"
        return format_html(
            '<a href="{}" class="button" style="margin-right: 5px; background-color: #2196F3; color: white;">{}</a>'
            '<a href="{}" class="button" style="background-color: #F44336; color: white;" onclick="return confirm(\'{}\')">{}</a>',
            change_url,
            _("Edit"),
            delete_url,
            _("Are you sure you want to delete this item?"),
            _("Delete"),
        )


class BaseSimpleAdmin(MixinActionAdmin):
    """Base admin for simple models with basic audit fields."""

    readonly_fields = ["created_at", "updated_at", "deleted_at"]
    list_display = ("__str__", "created_at", "updated_at", "action_buttons")
    search_fields = ("description", "name")

    def get_actions(self, request: HttpRequest) -> dict:
        """Remove Django's default delete action."""
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions


class BaseAuditAdmin(MixinActionAdmin):
    """Base admin with soft-delete, block/unblock, and audit functionalities."""

    readonly_fields = [
        "created_at",
        "updated_at",
        "deleted_at",
        "created_by",
        "updated_by",
        "deleted_by",
        "blocked_at",
        "blocked_by",
    ]

    actions = [
        "soft_delete_selected",
        "block_selected",
        "unblock_selected",
        "restore_selected",
        "export_excel",
    ]

    list_display = ("__str__", "created_at", "updated_at", "action_buttons")

    class Media:
        # Recommendation: Consolidate CSS/JS into fewer files if possible.
        css = {"all": ("css/admin/custom_admin.css",)}
        js = ("js/admin/custom_filters.js",)

    @admin.action(description=_("Mark as deleted (soft delete)"))
    def soft_delete_selected(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Action to soft delete selected records."""
        rows_updated = bulk_soft_delete(queryset=queryset, user=request.user)
        message = ngettext(
            "%(count)d record was marked as deleted.",
            "%(count)d records were marked as deleted.",
            rows_updated,
        ) % {"count": rows_updated}
        self.message_user(request, message, messages.SUCCESS)

    @admin.action(description=_("Block selected"))
    def block_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Action to block selected records."""
        rows_updated = bulk_block(queryset=queryset, user=request.user)
        message = ngettext(
            "%(count)d record was marked as blocked.",
            "%(count)d records were marked as blocked.",
            rows_updated,
        ) % {"count": rows_updated}
        self.message_user(request, message, messages.SUCCESS)

    @admin.action(description=_("Unblock selected"))
    def unblock_selected(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Action to unblock selected records."""
        rows_updated = bulk_unblock(queryset=queryset, user=request.user)
        message = ngettext(
            "%(count)d record was unblocked.",
            "%(count)d records were unblocked.",
            rows_updated,
        ) % {"count": rows_updated}
        self.message_user(request, message, messages.SUCCESS)

    @admin.action(description=_("Restore selected"))
    def restore_selected(
        self, request: HttpRequest, queryset: QuerySet
    ) -> None:
        """Action to restore deleted records."""
        rows_updated = bulk_restore(queryset=queryset, user=request.user)
        message = ngettext(
            "%(count)d record was restored.",
            "%(count)d records were restored.",
            rows_updated,
        ) % {"count": rows_updated}
        self.message_user(request, message, messages.SUCCESS)

    def get_actions(self, request: HttpRequest) -> dict:
        """Remove Django's default delete action."""
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def save_model(
        self, request: Any, obj: Any, form: Any, change: bool
    ) -> None:
        """Automatically set user on creation/update."""
        if not obj.pk:  # Set created_by only on creation
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_list_display(self, request: HttpRequest) -> tuple:
        """Customize list_display for non-superusers."""
        list_display = super().get_list_display(request)
        if not request.user.is_superuser:
            return tuple(
                f for f in list_display if not f.startswith("deleted_")
            )
        return list_display

    def _custom_success_message(
        self, request: HttpRequest, obj: Any, action: str
    ) -> None:
        """Display a custom success message."""
        name = getattr(obj, "name", str(obj))
        msg = _("%(action)s '%(name)s' was successful.") % {
            "action": action,
            "name": name,
        }

        currency = getattr(obj, "currency", "")
        forecast = getattr(obj, "forecast", None)
        if forecast is not None and currency:
            msg = _(
                "%(action)s '%(name)s' was successful. Forecast: %(currency)s %(forecast).2f"
            ) % {
                "action": action,
                "name": name,
                "currency": currency,
                "forecast": float(forecast),
            }
        messages.success(request, msg)

    def response_add(
        self,
        request: HttpRequest,
        obj: Any,
        post_url_override: str | None = None,
    ) -> HttpResponse:
        response = super().response_add(request, obj, post_url_override)
        if "_continue" not in request.POST:
            self._custom_success_message(request, obj, _("Created"))
        return response

    def response_change(self, request: HttpRequest, obj: Any) -> HttpResponse:
        response = super().response_change(request, obj)
        if "_continue" not in request.POST:
            self._custom_success_message(request, obj, _("Updated"))
        return response


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Admin configuration for the custom User model."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
        "change_password_button",
    )
    list_filter = ("is_staff", "is_active", "is_superuser", "last_login")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "last_login_ip",
                    "password_change_required",
                    "failed_login_attempts",
                    "last_password_change_at",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets

    def get_readonly_fields(
        self, request: HttpRequest, obj: User | None = None
    ) -> tuple:
        """Make certain fields read-only for non-superusers."""
        readonly = [
            "date_joined",
            "last_login",
            "last_login_ip",
            "last_password_change_at",
        ]
        if not request.user.is_superuser:
            readonly.extend(["is_superuser", "user_permissions"])
        return tuple(readonly)

    @admin.display(description=_("Change Password"))
    def change_password_button(self, obj: User) -> str:
        """Render a button to change the user's password."""
        if not obj.pk:
            return "-"
        url = f"/admin/core/user/{obj.pk}/password/"
        return format_html(
            '<a href="{}" class="btn button--warning" style="background-color: #FF9800; color: white;">{}</a>',
            url,
            _("Change Password"),
        )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    """Admin configuration for the Group model, using the Unfold theme."""

    pass
