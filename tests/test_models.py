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
Test cases for Order and OrderItem Models
"""

# pylint: disable=duplicate-code
import os
import logging
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from wsgi import app
from service.models import Order, OrderItem, DataValidationError, db
from .factories import OrderFactory, OrderItemFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql+psycopg://postgres:postgres@localhost:5432/testdb",
)


######################################################################
#  O R D E R   M O D E L   T E S T   C A S E S
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
        db.session.query(OrderItem).delete()
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
            status="pending",
            total_amount=Decimal("59.99"),
        )

        self.assertIsNotNone(order)
        self.assertIsNone(order.order_id)
        self.assertEqual(order.customer_id, 123)
        self.assertEqual(order.order_date, order_date)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.total_amount, Decimal("59.99"))

    def test_order_default_status(self):
        """It should default a new Order status to pending"""
        order = Order(
            customer_id=123,
            order_date=datetime.now(),
            total_amount=Decimal("59.99"),
        )

        order.create()

        self.assertEqual(order.status, "pending")

    def test_add_an_order(self):
        """It should create an Order and add it to the database"""
        orders = Order.all()
        self.assertEqual(orders, [])

        order = OrderFactory()
        order.create()

        self.assertIsNotNone(order.order_id)

        orders = Order.all()
        self.assertEqual(len(orders), 1)

    def test_read_an_order(self):
        """It should read an Order from the database"""
        order = OrderFactory()
        order.create()

        found_order = Order.find_by_order_id(order.order_id)

        self.assertIsNotNone(found_order)
        self.assertEqual(found_order.order_id, order.order_id)
        self.assertEqual(found_order.customer_id, order.customer_id)
        self.assertEqual(found_order.order_date, order.order_date)
        self.assertEqual(found_order.status, order.status)
        self.assertEqual(found_order.total_amount, order.total_amount)
        self.assertEqual(found_order.items, [])

    def test_update_an_order(self):
        """It should update an Order"""
        order = OrderFactory(status="pending")
        order.create()

        self.assertIsNotNone(order.order_id)
        self.assertEqual(order.status, "pending")

        order = Order.find_by_order_id(order.order_id)
        order.status = "processing"
        order.update()

        updated_order = Order.find_by_order_id(order.order_id)
        self.assertEqual(updated_order.status, "processing")

    def test_delete_an_order(self):
        """It should delete an Order from the database"""
        orders = Order.all()
        self.assertEqual(orders, [])

        order = OrderFactory()
        order.create()

        self.assertIsNotNone(order.order_id)

        orders = Order.all()
        self.assertEqual(len(orders), 1)

        order.delete()

        orders = Order.all()
        self.assertEqual(len(orders), 0)

    def test_serialize_an_order(self):
        """It should serialize an Order"""
        order = OrderFactory()
        order_item = OrderItemFactory(order=order)

        serialized_order = order.serialize()

        self.assertEqual(serialized_order["order_id"], order.order_id)
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

        self.assertEqual(len(serialized_order["items"]), 1)

        serialized_item = serialized_order["items"][0]
        self.assertEqual(serialized_item["id"], order_item.id)
        self.assertEqual(serialized_item["order_id"], order_item.order_id)
        self.assertEqual(serialized_item["product_id"], order_item.product_id)
        self.assertEqual(serialized_item["quantity"], order_item.quantity)
        self.assertEqual(serialized_item["price"], str(order_item.price))

    def test_deserialize_an_order(self):
        """It should deserialize an Order"""
        order = OrderFactory()
        order_item = OrderItemFactory(order=order)

        serialized_order = order.serialize()

        new_order = Order()
        new_order.deserialize(serialized_order)

        self.assertEqual(new_order.customer_id, order.customer_id)
        self.assertEqual(new_order.order_date, order.order_date)
        self.assertEqual(new_order.status, order.status)
        self.assertEqual(new_order.total_amount, order.total_amount)
        self.assertEqual(len(new_order.items), 1)

        new_item = new_order.items[0]
        self.assertEqual(new_item.product_id, order_item.product_id)
        self.assertEqual(new_item.quantity, order_item.quantity)
        self.assertEqual(new_item.price, order_item.price)

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

    def test_deserialize_order_item_with_key_error(self):
        """It should not deserialize an OrderItem with missing data"""
        order_item = OrderItem()

        self.assertRaises(
            DataValidationError,
            order_item.deserialize,
            {},
        )

    def test_deserialize_order_item_with_type_error(self):
        """It should not deserialize an OrderItem with invalid data"""
        order_item = OrderItem()

        self.assertRaises(
            DataValidationError,
            order_item.deserialize,
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
        """It should not update an Order without an order_id"""
        order = Order(
            customer_id=123,
            order_date=datetime.now(),
            status="pending",
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

    def test_add_order_item_to_order(self):
        """It should create an Order with an OrderItem and retrieve it"""
        order = OrderFactory()
        order_item = OrderItemFactory(order=order)

        order.create()

        self.assertIsNotNone(order.order_id)
        order_id = order.order_id

        db.session.expire_all()
        found_order = Order.find_by_order_id(order_id)

        self.assertIsNotNone(found_order)
        self.assertEqual(len(found_order.items), 1)

        found_item = found_order.items[0]
        self.assertEqual(found_item.product_id, order_item.product_id)
        self.assertEqual(found_item.quantity, order_item.quantity)
        self.assertEqual(found_item.price, order_item.price)
        self.assertEqual(found_item.order_id, found_order.order_id)

    def test_find_by_status(self):
        """It should Find Orders by status"""
        order1 = OrderFactory(status="pending")
        order2 = OrderFactory(status="cancelled")
        order3 = OrderFactory(status="pending")

        order1.create()
        order2.create()
        order3.create()

        orders = Order.find_by_status("pending")

        self.assertEqual(len(orders), 2)
        for order in orders:
            self.assertEqual(order.status, "pending")

    def test_deserialize_valid_order_data(self):
        """Scenario: Deserialize valid Order data populates model successfully"""
        valid_payload = {
            "customer_id": 101,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "99.99",
            "items": [{"product_id": 5, "quantity": 2, "price": "49.99"}],
        }

        order = Order()
        order.deserialize(valid_payload)

        self.assertEqual(order.customer_id, 101)
        self.assertEqual(order.status, "pending")
        self.assertEqual(len(order.items), 1)

    def test_deserialize_rejects_negative_customer_id(self):
        """Reject negative customer_id during deserialization"""
        bad_payload = {
            "customer_id": -5,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "10.00",
            "items": [],
        }

        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, bad_payload)

    def test_deserialize_rejects_invalid_status(self):
        """Reject invalid status value"""
        bad_payload = {
            "customer_id": 101,
            "order_date": "2026-10-20T12:00:00",
            "status": "fake_status",
            "total_amount": "10.00",
            "items": [],
        }

        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, bad_payload)

    def test_deserialize_rejects_negative_total_amount(self):
        """Reject negative total_amount value"""
        bad_payload = {
            "customer_id": 101,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "-50.00",
            "items": [],
        }

        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, bad_payload)

    def test_deserialize_rejects_items_not_list(self):
        """Reject items field that is not a list"""
        bad_payload = {
            "customer_id": 101,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "10.00",
            "items": "this-is-not-a-list",
        }

        order = Order()
        self.assertRaises(DataValidationError, order.deserialize, bad_payload)

    def test_deserialize_accepts_datetime_order_date(self):
        """Accept a datetime object for order_date."""
        order_date = datetime.now()
        order = Order()

        order.deserialize(
            {
                "customer_id": 101,
                "order_date": order_date,
                "items": [],
            }
        )

        self.assertEqual(order.order_date, order_date)

    def test_deserialize_rejects_invalid_order_date_type(self):
        """Reject an order_date that is neither a string nor datetime."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "order_date": 123,
                    "items": [],
                }
            )

    def test_deserialize_rejects_malformed_order_date(self):
        """Reject an invalid ISO-format order_date."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "order_date": "not-a-date",
                    "items": [],
                }
            )

    def test_deserialize_rejects_boolean_product_id(self):
        """Reject a boolean product_id."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": [
                        {
                            "product_id": True,
                            "quantity": 1,
                            "price": "1.00",
                        }
                    ],
                }
            )

    def test_deserialize_rejects_non_integer_quantity(self):
        """Reject a quantity that cannot be converted to an integer."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": "many",
                            "price": "1.00",
                        }
                    ],
                }
            )

    def test_deserialize_rejects_unparseable_item_price(self):
        """Reject a price that cannot be converted to Decimal."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": 1,
                            "price": "not-a-price",
                        }
                    ],
                }
            )

    def test_deserialize_rejects_negative_item_price(self):
        """Reject a negative item price."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": [
                        {
                            "product_id": 1,
                            "quantity": 1,
                            "price": "-1.00",
                        }
                    ],
                }
            )

    def test_deserialize_rejects_non_object_item(self):
        """Reject an item that is not a dictionary."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": ["not-an-item-object"],
                }
            )

    def test_deserialize_rejects_unparseable_total_amount(self):
        """Reject a total_amount that cannot be converted to Decimal."""
        order = Order()

        with self.assertRaises(DataValidationError):
            order.deserialize(
                {
                    "customer_id": 101,
                    "items": [],
                    "total_amount": "not-a-total",
                }
            )

    def test_deserialize_partial_total_amount(self):
        """Partial deserialization updates total and preserves other fields."""
        order = Order()
        order.deserialize(
            {
                "customer_id": 123,
                "status": "processing",
                "items": [
                    {"product_id": 1001, "quantity": 2, "price": "10.50"},
                ],
            }
        )

        original_order_date = order.order_date
        original_items = list(order.items)

        order.deserialize(
            {"total_amount": "25.75"},
            partial=True,
        )

        self.assertEqual(str(order.total_amount), "25.75")
        self.assertEqual(order.customer_id, 123)
        self.assertEqual(order.status, "processing")
        self.assertEqual(order.order_date, original_order_date)
        self.assertEqual(order.items, original_items)
