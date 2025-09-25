from django.db import models
from django.utils import timezone


class BaseQuerySet(models.QuerySet):
    """
    A base QuerySet that includes logic for soft-deletion.
    """

    def soft_delete(self, user):
        """Marks objects in the QuerySet as logically deleted."""
        return self.update(deleted_at=timezone.now(), deleted_by=user)

    def restore(self):
        """Restores objects in the QuerySet."""
        return self.update(deleted_at=None, deleted_by=None)

    def blocked(self, user):
        """
        Marks objects in the QuerySet as blocked.
        """
        return self.update(blocked_at=timezone.now(), blocked_by=user)

    def unblocked(self):
        """
        Marks objects in the QuerySet as unblocked.
        """
        return self.update(blocked_at=None, blocked_by=None)

    def hard_delete(self):
        """
        Performs a physical delete from the database.
        """
        return super().delete()

    def not_deleted(self):
        """
        Filters to include only non-deleted records.
        """
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """
        Filters to include only logically deleted records.
        """
        return self.filter(deleted_at__isnull=False)

    def created_by(self, user):
        """
        Filters to include only records created by the specified user.
        """
        return self.filter(created_by=user)

    def updated_by(self, user):
        """
        Filters to include only records updated by the specified user.
        """
        return self.filter(updated_by=user)

    def deleted_by(self, user):
        """
        Filters to include only records deleted by the specified user.
        """
        return self.filter(deleted_by=user)

    def created_after(self, date):
        """
        Filters to include only records created after the specified date.
        """
        return self.filter(created_at__gt=date)

    def created_before(self, date):
        """
        Filters to include only records created before the specified date.
        """
        return self.filter(created_at__lt=date)
