import uuid
from datetime import datetime

from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
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
    actions = ["export_excel"]

    @action(description=_("Export to Excel"), url_path="export-excel")
    def export_excel(self, request, queryset):
        """Export selected records to an Excel file."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = queryset.model.__name__ + "s"
        headers = [field.name for field in queryset.model._meta.fields]
        ws.append(headers)

        for obj in queryset:
            row = []
            for field in queryset.model._meta.fields:
                value = getattr(obj, field.name)
                if isinstance(value, uuid.UUID):
                    value = str(value)
                if isinstance(value, datetime) and value.tzinfo:
                    value = value.replace(tzinfo=None)
                elif isinstance(value, models.Model):
                    value = str(value)
                row.append(value)

            ws.append(row)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f"attachment; filename={queryset.model.__name__}_export.xlsx"
        )
        wb.save(response)
        return response

    def action_buttons(self, obj):
        """Custom action buttons for each row"""
        if obj.pk:
            opts = obj._meta
            app_label = opts.app_label
            model_name = opts.model_name
            edit_url = reverse(
                f"admin:{app_label}_{model_name}_change", args=[obj.pk]
            )
            delete_url = reverse(
                f"admin:{app_label}_{model_name}_delete", args=[obj.pk]
            )

            return format_html(
                '<a href="{}" class="button" style="margin-right: 5px; '
                "background-color: #2196F3; color: white; text-decoration: none; "
                'padding: 5px 10px; border-radius: 3px; font-size: 11px;">'
                "{}"
                "</a>"
                '<a href="{}" class="button" style="background-color: #F44336; '
                "color: white; text-decoration: none; padding: 5px 10px; "
                'border-radius: 3px; font-size: 11px;" '
                "onclick=\"return confirm('{}')\">"
                "{}"
                "</a>",
                edit_url,
                _("Edit"),
                delete_url,
                _("Are you sure you want to delete this opportunity?"),
                _("Delete"),
            )
        return "-"

    action_buttons.short_description = _("Actions")


class BaseSimpleAdmin(MixinActionAdmin):
    """
    Base admin for simple models with basic audit fields.
    """

    readonly_fields = ["created_at", "updated_at", "deleted_at"]
    list_display = ("__str__", "created_at", "updated_at", "action_buttons")
    search_fields = ("description", "name")

    def get_actions(self, request):
        """Removes Django's default delete action."""
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions


class BaseAuditAdmin(MixinActionAdmin):
    """
    Base admin with audit functionalities and custom actions.
    """

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
        *MixinActionAdmin.actions,
    ]

    list_display = ("action_buttons",)

    class Media:
        css = {"all": ("css/admin/opportunity_custom.css",)}
        js = ("js/admin/opportunity_filters.js",)

    @admin.action(description=_("Mark as deleted (soft delete)"))
    def soft_delete_selected(self, request, queryset):
        """Action to soft delete selected records"""
        rows_updated = bulk_soft_delete(queryset=queryset, user=request.user)
        self.message_user(
            request,
            f"{rows_updated} records marked as deleted.",
            messages.SUCCESS,
        )

    @admin.action(description=_("Block selected"))
    def block_selected(self, request, queryset):
        """Action to block selected records"""
        rows_updated = bulk_block(queryset=queryset, user=request.user)
        self.message_user(
            request,
            f"{rows_updated} records marked as blocked.",
            messages.SUCCESS,
        )

    @admin.action(description=_("Unblock selected"))
    def unblock_selected(self, request, queryset):
        """Action to unblock selected records"""
        rows_updated = bulk_unblock(queryset=queryset, user=request.user)
        self.message_user(
            request,
            f"{rows_updated} records unblocked.",
            messages.SUCCESS,
        )

    @admin.action(description=_("Restore selected"))
    def restore_selected(self, request, queryset):
        """Action to restore deleted records"""
        rows_updated = bulk_restore(queryset=queryset, user=request.user)
        self.message_user(
            request,
            f"{rows_updated} records restored.",
            messages.SUCCESS,
        )

    def get_actions(self, request):
        """Removes Django's default delete action."""
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def save_model(self, request, obj, form, change):
        """
        Automatically assigns the current user when creating/updating an object.
        """
        if not obj.created_at:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_list_display(self, request):
        """
        Allows customizing list_display based on user permissions.
        """
        list_display = super().get_list_display(request)
        if not request.user.is_superuser:
            return [
                field
                for field in list_display
                if not field.startswith("deleted_")
            ]
        return list_display

    def _custom_success_message(self, request, obj, action):
        """
        Displays a custom success message for add/change actions.
        Tries to use 'name', 'currency', and 'forecast' if available.
        """
        name = getattr(obj, "name", str(obj))
        currency = getattr(obj, "currency", "")
        forecast = getattr(obj, "forecast", None)
        if forecast is not None and currency:
            msg = _("{} '{}' {} successfully. Forecast: {} {:,.2f}").format(
                action, name, _("was"), currency, float(forecast)
            )
        else:
            msg = _("{} '{}' {} successfully.").format(action, name, _("was"))
        messages.success(request, msg)

    def response_add(self, request, obj, post_url_override=None):
        """Custom message when creating an object."""
        response = super().response_add(request, obj, post_url_override)
        self._custom_success_message(request, obj, _("Created"))
        return response

    def response_change(self, request, obj):
        """Custom message when updating an object."""
        response = super().response_change(request, obj)
        self._custom_success_message(request, obj, _("Updated"))
        return response


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """
    Admin configuration for the User model
    """

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
        "date_joined",
        "change_password_button",
    )
    search_fields = ("username", "email", "first_name", "last_name")
    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    ordering = ("-date_joined",)

    fieldsets = (
        (
            _("Personal Information"),
            {"fields": ("username", "email", "first_name", "last_name")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
        (
            _("Additional Information"),
            {
                "fields": (
                    "last_login_ip",
                    "password_change_required",
                    "failed_login_attempts",
                    "last_password_change_at",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Makes certain fields read-only for non-superusers"""
        readonly_fields = [
            "date_joined",
            "last_login",
            "last_login_ip",
            "last_password_change_at",
        ]
        if not request.user.is_superuser:
            readonly_fields.extend(["is_superuser", "user_permissions"])
        return readonly_fields

    @admin.display(description=_("Change Password"))
    def change_password_button(self, obj):
        """Render a button to change the user's password in admin."""
        if not obj or not obj.pk:
            return "-"
        url = f"/admin/core/user/{obj.pk}/password/"
        return format_html(
            '<a href="{}" class="button" style="background-color: #FF9800; '
            "color: white; text-decoration: none; padding: 5px 10px; "
            'border-radius: 3px; font-size: 11px;">{}</a>',
            url,
            _("Change Password"),
        )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
