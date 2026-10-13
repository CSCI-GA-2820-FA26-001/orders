######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Test cases for Order and Item Models
"""

# pylint: disable=duplicate-code
import os
import logging
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from wsgi import app
from service.models import Order, Item, DataValidationError, db
from .factories import OrderFactory, ItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)


######################################################################
#  Order   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestOrderModel(TestCase):
    """Test Cases for Order Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Item).delete()
        db.session.query(Order).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_an_order(self):
        """It should create an Order"""
        order_date = datetime.now()

        order = Order(
            customer_id=123,
            order_date=order_date,
            status="created",
            total_amount=Decimal("59.99"),
        )

        self.assertIsNotNone(order)
        self.assertIsNone(order.id)
        self.assertEqual(order.customer_id, 123)
        self.assertEqual(order.order_date, order_date)
        self.assertEqual(order.status, "created")
        self.assertEqual(order.total_amount, Decimal("59.99"))

    def test_add_an_order(self):
        """It should create an Order and add it to the database"""
        orders = Order.all()
        self.assertEqual(orders, [])

        order = OrderFactory()
        order.create()

        # Assert that it was assigned an id
        self.assertIsNotNone(order.id)

        # Assert that it shows up in the database
        orders = Order.all()
        self.assertEqual(len(orders), 1)

    def test_read_an_order(self):
        """It should read an Order from the database"""
        order = OrderFactory()
        order.create()

        # Read it back
        found_order = Order.find(order.id)

        self.assertIsNotNone(found_order)
        self.assertEqual(found_order.id, order.id)
        self.assertEqual(found_order.customer_id, order.customer_id)
        self.assertEqual(found_order.order_date, order.order_date)
        self.assertEqual(found_order.status, order.status)
        self.assertEqual(found_order.total_amount, order.total_amount)
        self.assertEqual(found_order.items, [])

    def test_update_an_order(self):
        """It should update an Order"""
        order = OrderFactory(status="created")
        order.create()

        # Assert that it was assigned an id
        self.assertIsNotNone(order.id)
        self.assertEqual(order.status, "created")

        # Fetch it back
        order = Order.find(order.id)

        # Change the status
        order.status = "processing"
        order.update()

        # Fetch it back again
        updated_order = Order.find(order.id)

        self.assertEqual(updated_order.status, "processing")

    def test_delete_an_order(self):
        """It should delete an Order from the database"""
        orders = Order.all()
        self.assertEqual(orders, [])

        order = OrderFactory()
        order.create()

        # Assert that it was assigned an id
        self.assertIsNotNone(order.id)

        # Assert that it shows up in the database
        orders = Order.all()
        self.assertEqual(len(orders), 1)

        # Delete the order
        order.delete()

        # Assert that it was removed from the database
        orders = Order.all()
        self.assertEqual(len(orders), 0)

    def test_serialize_an_order(self):
        """It should serialize an Order"""
        order = OrderFactory()
        item = ItemFactory(order=order)

        serialized_order = order.serialize()

        self.assertEqual(serialized_order["id"], order.id)
        self.assertEqual(serialized_order["customer_id"], order.customer_id)
        self.assertEqual(
            serialized_order["order_date"],
            order.order_date.isoformat(),
        )
        self.assertEqual(serialized_order["status"], order.status)
        self.assertEqual(
            serialized_order["total_amount"],
            str(order.total_amount),
        )

        # Assert that the Item is included in the Order
        self.assertEqual(len(serialized_order["items"]), 1)

        serialized_item = serialized_order["items"][0]
        self.assertEqual(serialized_item["id"], item.id)
        self.assertEqual(serialized_item["order_id"], item.order_id)
        self.assertEqual(serialized_item["product_id"], item.product_id)
        self.assertEqual(serialized_item["quantity"], item.quantity)
        self.assertEqual(serialized_item["price"], str(item.price))

    def test_deserialize_an_order(self):
        """It should deserialize an Order"""
        order = OrderFactory()
        item = ItemFactory(order=order)

        serialized_order = order.serialize()

        new_order = Order()
        new_order.deserialize(serialized_order)

        self.assertEqual(new_order.customer_id, order.customer_id)
        self.assertEqual(new_order.order_date, order.order_date)
        self.assertEqual(new_order.status, order.status)
        self.assertEqual(new_order.total_amount, order.total_amount)

        # Assert that the Item was also deserialized
        self.assertEqual(len(new_order.items), 1)

        new_item = new_order.items[0]
        self.assertEqual(new_item.product_id, item.product_id)
        self.assertEqual(new_item.quantity, item.quantity)
        self.assertEqual(new_item.price, item.price)

    def test_deserialize_order_with_key_error(self):
        """It should not deserialize an Order with missing data"""
        order = Order()

        self.assertRaises(
            DataValidationError,
            order.deserialize,
            {},
        )

    def test_deserialize_order_with_type_error(self):
        """It should not deserialize an Order with invalid data"""
        order = Order()

        self.assertRaises(
            DataValidationError,
            order.deserialize,
            [],
        )

    def test_deserialize_item_with_key_error(self):
        """It should not deserialize an Item with missing data"""
        item = Item()

        self.assertRaises(
            DataValidationError,
            item.deserialize,
            {},
        )

    def test_deserialize_item_with_type_error(self):
        """It should not deserialize an Item with invalid data"""
        item = Item()

        self.assertRaises(
            DataValidationError,
            item.deserialize,
            [],
        )

    @patch("service.models.db.session.commit")
    def test_add_order_failed(self, exception_mock):
        """It should not create an Order on database error"""
        exception_mock.side_effect = Exception()

        order = OrderFactory()

        self.assertRaises(
            DataValidationError,
            order.create,
        )

    def test_update_order_with_no_id(self):
        """It should not update an Order without an id"""
        order = Order(
            customer_id=123,
            order_date=datetime.now(),
            status="created",
            total_amount=Decimal("59.99"),
        )

        self.assertRaises(
            DataValidationError,
            order.update,
        )

    @patch("service.models.db.session.commit")
    def test_update_order_failed(self, exception_mock):
        """It should not update an Order on database error"""
        exception_mock.side_effect = Exception()

        order = OrderFactory()

        self.assertRaises(
            DataValidationError,
            order.update,
        )

    @patch("service.models.db.session.commit")
    def test_delete_order_failed(self, exception_mock):
        """It should not delete an Order on database error"""
        exception_mock.side_effect = Exception()

        order = OrderFactory()

        self.assertRaises(
            DataValidationError,
            order.delete,
        )

    def test_add_item_to_order(self):
        """It should create an Order with an Item and retrieve the Item"""
        order = OrderFactory()
        item = ItemFactory(order=order)

        # Save the Order and its related Item
        order.create()

        self.assertIsNotNone(order.id)

        # Force SQLAlchemy to reload data from the database
        db.session.expire_all()

        # Fetch the Order back
        found_order = Order.find(order.id)

        self.assertIsNotNone(found_order)
        self.assertEqual(len(found_order.items), 1)

        # Verify the Item was persisted with the Order
        found_item = found_order.items[0]

        self.assertEqual(found_item.product_id, item.product_id)
        self.assertEqual(found_item.quantity, item.quantity)
        self.assertEqual(found_item.price, item.price)
        self.assertEqual(found_item.order_id, found_order.id)
