from django.db import models

from .querysets import BaseQuerySet


class BaseManager(models.Manager):
    """
    Manager that uses the BaseQuerySet to enforce soft-delete logic by default.
    """

    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db).not_deleted()

    def all_with_deleted(self):
        """
        Returns all objects, including logically deleted ones.
        """
        return BaseQuerySet(self.model, using=self._db)

    def restore(self):
        """
        Restores logically deleted objects in the QuerySet.
        """
        return self.get_queryset().restore()
    
    def deleted(self):
        """
        Returns only logically deleted objects.
        """
        return BaseQuerySet(self.model, using=self._db).deleted()

    def hard_delete(self):
        """
        Performs a physical delete from the database.
        """
        return self.get_queryset().hard_delete()

    def soft_delete(self, user):
        """
        Marks objects in the QuerySet as logically deleted.
        """
        return self.get_queryset().soft_delete(user)

    def blocked(self, user):
        """
        Marks objects in the QuerySet as blocked.
        """
        return self.get_queryset().blocked(user)

    def unblocked(self):
        """
        Marks objects in the QuerySet as unblocked.
        """
        return self.get_queryset().unblocked()
