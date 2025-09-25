from django.db import models, transaction

from .models import BaseModel, User


@transaction.atomic
def soft_delete_instance(instance: BaseModel, user: User) -> BaseModel:
    """
    Performs a soft delete on a single model instance.
    """
    if instance.is_deleted():
        return instance

    instance_queryset = instance.__class__.objects.all_with_deleted().filter(
        pk=instance.pk
    )
    instance_queryset.soft_delete(user)

    instance.refresh_from_db()
    return instance


@transaction.atomic
def restore_instance(instance: BaseModel, user: User) -> BaseModel:
    """
    Restores a single logically deleted model instance.
    """
    if not instance.is_deleted():
        return instance

    instance_queryset = instance.__class__.objects.all_with_deleted().filter(
        pk=instance.pk
    )
    instance_queryset.restore()

    instance.refresh_from_db()
    return instance


@transaction.atomic
def block_instance(instance: BaseModel, user: User) -> BaseModel:
    """
    Marks a single model instance as blocked.
    """
    instance_queryset = instance.__class__.objects.all_with_deleted().filter(
        pk=instance.pk
    )
    instance_queryset.blocked(user)

    instance.refresh_from_db()
    return instance


@transaction.atomic
def unblock_instance(instance: BaseModel, user: User) -> BaseModel:
    """
    Marks a single model instance as unblocked.
    """
    instance_queryset = instance.__class__.objects.all_with_deleted().filter(
        pk=instance.pk
    )
    instance_queryset.unblocked()

    instance.refresh_from_db()
    return instance


@transaction.atomic
def bulk_soft_delete(queryset: models.QuerySet, user: User) -> int:
    """
    Performs a bulk soft delete operation on a QuerySet.
    """
    rows_updated = queryset.soft_delete(user)

    return rows_updated


@transaction.atomic
def bulk_restore(queryset: models.QuerySet, user: User) -> int:
    """
    Performs a bulk restore operation on a QuerySet.
    """
    queryset_deleted = queryset.deleted()
    rows_updated = queryset_deleted.restore()
    return rows_updated


@transaction.atomic
def bulk_block(queryset: models.QuerySet, user: User) -> int:
    """
    Performs a bulk block operation on a QuerySet.
    """
    rows_updated = queryset.blocked(user)
    return rows_updated


@transaction.atomic
def bulk_unblock(queryset: models.QuerySet, user: User) -> int:
    """
    Performs a bulk unblock operation on a QuerySet.
    """
    rows_updated = queryset.unblocked()
    return rows_updated
