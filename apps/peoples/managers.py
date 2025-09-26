from django.db import models

from apps.core.managers import BaseManager

from .querysets import AddressQuerySet


class PersonManager(BaseManager):
    """
    Custom Manager for the Person model.
    """

    pass


class AddressManager(models.Manager):
    """
    Custom Manager for the Address model.
    """

    def get_queryset(self):
        return AddressQuerySet(self.model, using=self._db)

    def create_address(
        self,
        person,
        label,
        department,
        province,
        district,
        address,
        **kwargs,
    ):
        """
        Creates an address for a given person, handling default and billing logic.
        """
        is_default = kwargs.pop("is_default", False)
        is_billing = kwargs.pop("is_billing", False)

        if is_default:
            self.filter(person=person).update(is_default=False)
        if is_billing:
            self.filter(person=person).update(is_billing=False)

        return self.create(
            person=person,
            label=label,
            department=department,
            province=province,
            district=district,
            address=address,
            is_default=is_default,
            is_billing=is_billing,
            **kwargs,
        )

    def update_address(self, address_instance, **kwargs):
        """
        Updates an existing address, handling default and billing logic.
        """
        is_default = kwargs.pop("is_default", None)
        is_billing = kwargs.pop("is_billing", None)

        if is_default is not None and is_default:
            self.filter(person=address_instance.person).exclude(
                pk=address_instance.pk
            ).update(is_default=False)
        if is_billing is not None and is_billing:
            self.filter(person=address_instance.person).exclude(
                pk=address_instance.pk
            ).update(is_billing=False)

        for attr, value in kwargs.items():
            setattr(address_instance, attr, value)
        address_instance.save()
        return address_instance
