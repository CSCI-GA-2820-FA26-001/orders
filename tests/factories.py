"""
Test Factory to make fake objects for testing
"""

from datetime import datetime
from decimal import Decimal

import factory
from factory import Factory, SubFactory, Sequence, post_generation

from service.models import Order, OrderItem


class OrderFactory(Factory):
    """Creates fake Orders"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to Order model"""

        model = Order

    id = Sequence(lambda n: n)
    customer_id = Sequence(lambda n: n + 1000)
    order_date = factory.LazyFunction(datetime.now)
    status = "pending"
    total_amount = factory.LazyFunction(lambda: Decimal("59.99"))

    @post_generation
    def items(
        self, create, extracted, **kwargs
    ):  # pylint: disable=method-hidden, unused-argument
        """Creates the OrderItems list"""
        if not create:
            return

        if extracted:
            self.items = extracted


class OrderItemFactory(Factory):
    """Creates fake OrderItems"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Maps factory to OrderItem model"""

        model = OrderItem

    id = Sequence(lambda n: n)
    order_id = None
    product_id = Sequence(lambda n: n + 2000)
    quantity = factory.Faker("random_int", min=1, max=10)
    price = factory.LazyFunction(lambda: Decimal("19.99"))
    order = SubFactory(OrderFactory)
