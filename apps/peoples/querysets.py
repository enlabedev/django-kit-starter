from django.db.models import QuerySet


class PersonQuerySet(QuerySet):
    """
    Custom QuerySet for the Person model.
    """

    pass


class AddressQuerySet(QuerySet):
    """
    Custom QuerySet for the Address model.
    """

    def default(self):
        return self.filter(is_default=True)

    def billing(self):
        return self.filter(is_billing=True)
