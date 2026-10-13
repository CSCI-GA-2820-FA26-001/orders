"""
Test Factory to make fake objects for testing
"""

from datetime import datetime
from decimal import Decimal

import factory
from factory import Factory, SubFactory, Sequence, Faker, post_generation
from factory.fuzzy import FuzzyChoice

from service.models import Order, Item


class OrderFactory(Factory):
    """Creates fake Orders"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to Order model"""

        model = Order

    id = Sequence(lambda n: n)
    customer_id = Sequence(lambda n: n + 1000)
    order_date = factory.LazyFunction(datetime.now)
    status = FuzzyChoice(choices=["created", "processing", "completed", "cancelled"])
    total_amount = factory.LazyFunction(lambda: Decimal("59.99"))

    # The many side of relationships can be a little wonky in factory boy
    @post_generation
    def items(
        self, create, extracted, **kwargs
    ):  # pylint: disable=method-hidden, unused-argument
        """Creates the items list"""
        if not create:
            return

        if extracted:
            self.items = extracted


class ItemFactory(Factory):
    """Creates fake Order Items"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to Item model"""

        model = Item

    id = Sequence(lambda n: n)
    order_id = None
    product_id = Sequence(lambda n: n + 2000)
    quantity = Faker("random_int", min=1, max=10)
    price = factory.LazyFunction(lambda: Decimal("19.99"))
    order = SubFactory(OrderFactory)
