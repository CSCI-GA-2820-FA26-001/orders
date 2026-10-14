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
Orders API Service Test Suite
"""

# pylint: disable=duplicate-code
import os
import logging
from unittest import TestCase
from unittest.mock import patch

from flask import abort
from wsgi import app
from service.common import status
from service.models import db, Order, OrderItem

DATABASE_URI = os.getenv(
    "DATABASE_URI",
    "postgresql+psycopg://postgres:postgres@localhost:5432/testdb",
)


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestOrderService(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False

        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()

        db.session.query(OrderItem).delete()
        db.session.query(Order).delete()
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(
            resp.status_code,
            status.HTTP_200_OK,
        )

    def test_bad_request(self):
        """It should return 400 Bad Request"""
        with patch.dict(
            app.view_functions,
            {"index": lambda: abort(status.HTTP_400_BAD_REQUEST)},
        ):
            resp = self.client.get("/")
            self.assertEqual(
                resp.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

    def test_not_found(self):
        """It should return 404 Not Found"""
        resp = self.client.get("/this-route-does-not-exist")

        self.assertEqual(
            resp.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_method_not_allowed(self):
        """It should return 405 Method Not Allowed"""
        resp = self.client.post("/")

        self.assertEqual(
            resp.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_unsupported_media_type(self):
        """It should return 415 Unsupported Media Type"""
        with patch.dict(
            app.view_functions,
            {"index": lambda: abort(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)},
        ):
            resp = self.client.get("/")
            self.assertEqual(
                resp.status_code,
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

    def test_internal_server_error(self):
        """It should return 500 Internal Server Error"""
        with patch.dict(
            app.view_functions,
            {"index": lambda: abort(status.HTTP_500_INTERNAL_SERVER_ERROR)},
        ):
            resp = self.client.get("/")
            self.assertEqual(
                resp.status_code,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def test_create_order(self):
        """It should Create a new Order"""
        payload = {
            "customer_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 2,
                    "price": "10.50",
                },
                {
                    "product_id": 1002,
                    "quantity": 1,
                    "price": "5.00",
                },
            ],
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_201_CREATED,
        )

        data = resp.get_json()

        self.assertEqual(data["customer_id"], 123)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["total_amount"], "26.00")
        self.assertEqual(len(data["items"]), 2)

        self.assertIn("Location", resp.headers)
        self.assertEqual(
            resp.headers["Location"],
            f"/orders/{data['order_id']}",
        )

        # Verify that the Order was saved
        order = Order.find(data["order_id"])

        self.assertIsNotNone(order)
        self.assertEqual(order.customer_id, 123)
        self.assertEqual(len(order.items), 2)

    def test_create_order_missing_customer_id(self):
        """It should not Create an Order without customer_id"""
        payload = {
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 2,
                    "price": "10.50",
                }
            ]
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(resp.is_json)

    def test_create_order_no_data(self):
        """It should not Create an Order with no data"""
        resp = self.client.post(
            "/orders",
            json={},
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(resp.is_json)

    def test_create_order_missing_items(self):
        """It should not Create an Order without items"""
        payload = {
            "customer_id": 123,
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(resp.is_json)

    def test_create_order_empty_items(self):
        """It should not Create an Order with empty items"""
        payload = {
            "customer_id": 123,
            "items": [],
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(resp.is_json)

    def test_create_order_invalid_item(self):
        """It should not Create an Order with an invalid item"""
        payload = {
            "customer_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 2,
                }
            ],
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(resp.is_json)

    def test_create_order_invalid_quantity(self):
        """It should not Create an Order with an invalid quantity"""
        payload = {
            "customer_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 0,
                    "price": "10.50",
                }
            ],
        }

        resp = self.client.post(
            "/orders",
            json=payload,
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(resp.is_json)
