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
        """It should return service metadata at the root URL"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["name"], "Orders Service")
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["list_url"], "/orders")


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

    def test_get_order(self):
        """It should retrieve an existing Order by id"""
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

        create_resp = self.client.post("/orders", json=payload)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        created = create_resp.get_json()
        order_id = created["order_id"]

        resp = self.client.get(f"/orders/{order_id}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["customer_id"], 123)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["total_amount"], "26.00")
        self.assertIn("order_date", data)
        self.assertIsNotNone(data["order_date"])

    def test_get_order_not_found(self):
        """It should return 404 when the Order does not exist"""
        resp = self.client.get("/orders/0")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)
        self.assertNotIn("order_id", data)
        self.assertNotIn("customer_id", data)
        self.assertNotIn("order_date", data)
        self.assertNotIn("total_amount", data)
        self.assertNotIn("items", data)

    def test_delete_order(self):
        """It should Delete an Order"""
        payload = {
            "customer_id": 123,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 2,
                    "price": "10.50",
                }
            ],
        }

        create_resp = self.client.post("/orders", json=payload)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        resp = self.client.delete(f"/orders/{order_id}")

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

        self.assertIsNone(Order.find_by_order_id(order_id))
        self.assertEqual(
            OrderItem.query.filter_by(order_id=order_id).count(),
            0,
        )

        get_resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_order_not_found(self):
        """It should return 404 when deleting an Order that does not exist"""
        resp = self.client.delete("/orders/888")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)

    def test_get_order_item(self):
        """It should Read a single Item from an Order"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
                {"product_id": 1002, "quantity": 1, "price": "5.00"},
            ],
        }

        create_resp = self.client.post("/orders", json=payload)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order = create_resp.get_json()
        order_id = order["order_id"]
        item = order["items"][1]

        resp = self.client.get(f"/orders/{order_id}/items/{item['id']}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertEqual(data["id"], item["id"])
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["product_id"], 1002)
        self.assertEqual(data["quantity"], 1)
        self.assertEqual(data["price"], "5.00")

    def test_get_order_item_order_not_found(self):
        """It should return 404 when reading an Item from an Order that does not exist"""
        resp = self.client.get("/orders/0/items/1")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Order with id '0' was not found", data["message"])

    def test_get_order_item_not_found(self):
        """It should return 404 when the Item does not exist"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
            ],
        }

        create_resp = self.client.post("/orders", json=payload)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        resp = self.client.get(f"/orders/{order_id}/items/0")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Item with id '0' was not found", data["message"])

    def test_get_order_item_wrong_order(self):
        """It should return 404 when the Item belongs to a different Order"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
            ],
        }

        order_a = self.client.post("/orders", json=payload).get_json()
        order_b = self.client.post("/orders", json=payload).get_json()
        item_b_id = order_b["items"][0]["id"]

        resp = self.client.get(f"/orders/{order_a['order_id']}/items/{item_b_id}")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn(f"Item with id '{item_b_id}' was not found", data["message"])

        # The same Item is still readable through its own Order
        resp = self.client.get(f"/orders/{order_b['order_id']}/items/{item_b_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
