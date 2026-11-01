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

# pylint: disable=duplicate-code,too-many-lines
import os
import logging
from decimal import Decimal
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

    def test_health(self):
        """It should report that the service is healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        self.assertEqual(resp.get_json(), {"status": "OK"})

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
            f"http://localhost/orders/{data['order_id']}",
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
            status.HTTP_201_CREATED,
        )
        data = resp.get_json()
        self.assertEqual(data["customer_id"], 123)
        self.assertEqual(data.get("items", []), [])
        self.assertEqual(data["total_amount"], "0.00")

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
            status.HTTP_201_CREATED,
        )
        data = resp.get_json()
        self.assertEqual(data["customer_id"], 123)
        self.assertEqual(data.get("items", []), [])
        self.assertEqual(data["total_amount"], "0.00")

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
        """It should return 204 when deleting an Order that does not exist"""
        resp = self.client.delete("/orders/888")

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

    def test_delete_order_idempotent(self):
        """It should return 204 when deleting the same Order twice"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [
                    {
                        "product_id": 1001,
                        "quantity": 1,
                        "price": "10.00",
                    }
                ],
            },
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        first = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(first.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(first.data, b"")
        self.assertIsNone(Order.find_by_order_id(order_id))

        second = self.client.delete(f"/orders/{order_id}")
        self.assertEqual(second.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second.data, b"")

    def _create_order_with_status(self, order_status):
        """Creates an Order through the API and sets its status"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [
                    {
                        "product_id": 1001,
                        "quantity": 2,
                        "price": "10.50",
                    }
                ],
            },
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        order = Order.find(order_id)
        order.status = order_status
        order.update()
        return order_id

    def test_cancel_order(self):
        """It should Cancel a pending Order"""
        order_id = self._create_order_with_status("pending")

        resp = self.client.put(f"/orders/{order_id}/cancel")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["status"], "cancelled")
        self.assertEqual(len(data["items"]), 1)

        saved_order = Order.find(order_id)
        self.assertEqual(saved_order.status, "cancelled")

    def test_cancel_order_not_found(self):
        """It should return 404 when cancelling an Order that does not exist"""
        resp = self.client.put("/orders/0/cancel")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)

    def test_cancel_order_not_pending(self):
        """It should not Cancel an Order that is not pending"""
        for order_status in ("processing", "shipped", "delivered", "cancelled"):
            with self.subTest(status=order_status):
                order_id = self._create_order_with_status(order_status)

                resp = self.client.put(f"/orders/{order_id}/cancel")

                self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
                self.assertTrue(resp.is_json)

                data = resp.get_json()
                self.assertEqual(data["error"], "Conflict")
                self.assertEqual(data["status"], status.HTTP_409_CONFLICT)

                saved_order = Order.find(order_id)
                self.assertEqual(saved_order.status, order_status)

    def test_update_order(self):
        """It should update the customer_id of an existing Order"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [
                    {
                        "product_id": 1001,
                        "quantity": 2,
                        "price": "10.50",
                    }
                ],
            },
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        resp = self.client.put(
            f"/orders/{order_id}",
            json={"customer_id": 456},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["customer_id"], 456)
        self.assertEqual(len(data["items"]), 1)

        saved_order = Order.find(order_id)
        self.assertEqual(saved_order.customer_id, 456)
        self.assertEqual(len(saved_order.items), 1)

    def test_update_order_not_found(self):
        """It should return JSON 404 when the Order does not exist"""
        resp = self.client.put(
            "/orders/0",
            json={"customer_id": 456},
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertEqual(data["status"], status.HTTP_404_NOT_FOUND)

    def test_update_order_invalid_payload(self):
        """It should return JSON 400 for an incomplete or invalid payload"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [
                    {
                        "product_id": 1001,
                        "quantity": 1,
                        "price": "10.50",
                    }
                ],
            },
        )
        order_id = create_resp.get_json()["order_id"]

        invalid_payloads = [
            {},
            {"customer_id": 0},
            {"customer_id": "456"},
            {"customer_id": 456, "items": []},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                resp = self.client.put(f"/orders/{order_id}", json=payload)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertTrue(resp.is_json)

    def test_list_orders(self):
        """It should list all orders"""
        first_payload = {
            "customer_id": 42,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 1,
                    "price": "10.00",
                }
            ],
        }
        second_payload = {
            "customer_id": 10,
            "items": [
                {
                    "product_id": 1002,
                    "quantity": 1,
                    "price": "5.00",
                }
            ],
        }

        first_create = self.client.post("/orders", json=first_payload)
        second_create = self.client.post("/orders", json=second_payload)

        self.assertEqual(first_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_create.status_code, status.HTTP_201_CREATED)

        first_order = first_create.get_json()
        second_order = second_create.get_json()

        resp = self.client.get("/orders")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        returned_order_ids = {order["order_id"] for order in data}
        self.assertEqual(
            returned_order_ids,
            {first_order["order_id"], second_order["order_id"]},
        )

    def test_list_orders_by_customer_id(self):
        """It should list only orders for the requested customer"""
        customer_42_payload = {
            "customer_id": 42,
            "items": [
                {
                    "product_id": 1001,
                    "quantity": 1,
                    "price": "10.00",
                }
            ],
        }
        customer_10_payload = {
            "customer_id": 10,
            "items": [
                {
                    "product_id": 1002,
                    "quantity": 1,
                    "price": "5.00",
                }
            ],
        }

        first_create = self.client.post("/orders", json=customer_42_payload)
        second_create = self.client.post("/orders", json=customer_42_payload)
        other_create = self.client.post("/orders", json=customer_10_payload)

        self.assertEqual(first_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(other_create.status_code, status.HTTP_201_CREATED)

        resp = self.client.get("/orders?customer_id=42")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(order["customer_id"] == 42 for order in data))

    def test_list_orders_empty(self):
        """It should return an empty list when there are no orders"""
        resp = self.client.get("/orders")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        self.assertEqual(resp.get_json(), [])

    def test_add_item_to_order(self):
        """It should add an item to an existing Order"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [{"product_id": 1001, "quantity": 1, "price": "10.50"}],
            },
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        resp = self.client.post(
            f"/orders/{order_id}/items",
            json={"product_id": 1002, "quantity": 2, "price": "5.25"},
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        item_data = resp.get_json()
        self.assertIn("id", item_data)
        self.assertEqual(item_data["product_id"], 1002)
        self.assertEqual(item_data["quantity"], 2)
        self.assertEqual(item_data["price"], "5.25")
        self.assertEqual(
            resp.headers["Location"],
            f"http://localhost/orders/{order_id}/items/{item_data['id']}",
        )

        saved_order = Order.find(order_id)
        self.assertEqual(len(saved_order.items), 2)
        self.assertEqual(saved_order.total_amount, Decimal("21.00"))

    def test_add_item_to_order_not_found(self):
        """It should return 404 when adding an item to a missing Order"""
        resp = self.client.post(
            "/orders/0/items",
            json={"product_id": 1002, "quantity": 1, "price": "5.25"},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_item_to_order_invalid_payload(self):
        """It should return 400 for an incomplete or invalid item payload"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [{"product_id": 1001, "quantity": 1, "price": "10.50"}],
            },
        )
        order_id = create_resp.get_json()["order_id"]
        url = f"/orders/{order_id}/items"

        payloads = [
            [],
            {},
            {"quantity": 1, "price": "5.25"},
            {"product_id": 1002, "price": "5.25"},
            {"product_id": 1002, "quantity": 1},
            {"product_id": "1002", "quantity": 1, "price": "5.25"},
            {"product_id": 0, "quantity": 1, "price": "5.25"},
            {"product_id": 1002, "quantity": True, "price": "5.25"},
            {"product_id": 1002, "quantity": 0, "price": "5.25"},
            {"product_id": 1002, "quantity": 1, "price": "invalid"},
            {"product_id": 1002, "quantity": 1, "price": "-1.00"},
            {"product_id": 1002, "quantity": 1, "price": "NaN"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                resp = self.client.post(url, json=payload)
                self.assertEqual(
                    resp.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

    def test_list_orders_invalid_customer_id(self):
        """It should return 400 when customer_id is not an integer"""
        resp = self.client.get("/orders?customer_id=abc")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_order_rejects_boolean_customer_id(self):
        """It should return 400 when customer_id is a boolean"""
        create_resp = self.client.post(
            "/orders",
            json={
                "customer_id": 123,
                "items": [{"product_id": 1001, "quantity": 1, "price": "10.50"}],
            },
        )
        order_id = create_resp.get_json()["order_id"]

        resp = self.client.put(
            f"/orders/{order_id}",
            json={"customer_id": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_order_items(self):
        """It should List all Items in an Order"""
        payload_a = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
                {"product_id": 1002, "quantity": 1, "price": "5.00"},
            ],
        }
        payload_b = {
            "customer_id": 456,
            "items": [
                {"product_id": 1003, "quantity": 3, "price": "7.25"},
            ],
        }

        create_resp = self.client.post("/orders", json=payload_a)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        order_id = create_resp.get_json()["order_id"]

        create_resp = self.client.post("/orders", json=payload_b)
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"/orders/{order_id}/items")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertEqual(len(data), 2)

        for item in data:
            self.assertIn("id", item)
            self.assertEqual(item["order_id"], order_id)

        items = sorted(data, key=lambda item: item["product_id"])
        self.assertEqual(items[0]["product_id"], 1001)
        self.assertEqual(items[0]["quantity"], 2)
        self.assertEqual(items[0]["price"], "10.50")
        self.assertEqual(items[1]["product_id"], 1002)
        self.assertEqual(items[1]["quantity"], 1)
        self.assertEqual(items[1]["price"], "5.00")

    def test_list_order_items_empty(self):
        """It should return an empty list for an Order with no Items"""
        order = Order()
        order.customer_id = 123
        order.create()

        resp = self.client.get(f"/orders/{order.id}/items")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_list_order_items_order_not_found(self):
        """It should return 404 when listing Items for an Order that does not exist"""
        resp = self.client.get("/orders/0/items")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Order with id '0' was not found", data["message"])

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

    def test_update_order_item(self):
        """It should Update an Item in an Order and recalculate the total"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
                {"product_id": 1002, "quantity": 1, "price": "5.00"},
            ],
        }

        order = self.client.post("/orders", json=payload).get_json()
        order_id = order["order_id"]
        self.assertEqual(order["total_amount"], "26.00")
        item = next(i for i in order["items"] if i["product_id"] == 1001)
        other = next(i for i in order["items"] if i["product_id"] == 1002)

        resp = self.client.put(
            f"/orders/{order_id}/items/{item['id']}",
            json={"product_id": 2001, "quantity": 3, "price": "4.00"},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertEqual(data["id"], item["id"])
        self.assertEqual(data["order_id"], order_id)
        self.assertEqual(data["product_id"], 2001)
        self.assertEqual(data["quantity"], 3)
        self.assertEqual(data["price"], "4.00")

        # The change is persisted and the total reflects it
        resp = self.client.get(f"/orders/{order_id}/items/{item['id']}")
        self.assertEqual(resp.get_json(), data)

        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.get_json()["total_amount"], "17.00")

        # The other Item is untouched
        resp = self.client.get(f"/orders/{order_id}/items/{other['id']}")
        self.assertEqual(resp.get_json(), other)

    def test_update_order_item_ignores_order_id(self):
        """It should not move an Item to another Order through the payload"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order_a = self.client.post("/orders", json=payload).get_json()
        order_b = self.client.post("/orders", json=payload).get_json()
        item = order_a["items"][0]

        resp = self.client.put(
            f"/orders/{order_a['order_id']}/items/{item['id']}",
            json={
                "order_id": order_b["order_id"],
                "product_id": 1001,
                "quantity": 1,
                "price": "10.50",
            },
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["order_id"], order_a["order_id"])

        resp = self.client.get(f"/orders/{order_a['order_id']}")
        self.assertEqual(resp.get_json()["total_amount"], "10.50")

        resp = self.client.get(f"/orders/{order_b['order_id']}")
        self.assertEqual(resp.get_json()["total_amount"], "21.00")

    def test_update_order_item_order_not_found(self):
        """It should return 404 when updating an Item in an Order that does not exist"""
        resp = self.client.put(
            "/orders/0/items/1",
            json={"product_id": 1001, "quantity": 1, "price": "1.00"},
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Order with id '0' was not found", data["message"])

    def test_update_order_item_not_found(self):
        """It should return 404 when the Item to update does not exist"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order_id = self.client.post("/orders", json=payload).get_json()["order_id"]

        resp = self.client.put(
            f"/orders/{order_id}/items/0",
            json={"product_id": 1001, "quantity": 1, "price": "1.00"},
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Item with id '0' was not found", data["message"])

    def test_update_order_item_wrong_order(self):
        """It should not update an Item that belongs to a different Order"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order_a = self.client.post("/orders", json=payload).get_json()
        order_b = self.client.post("/orders", json=payload).get_json()
        item_b = order_b["items"][0]

        resp = self.client.put(
            f"/orders/{order_a['order_id']}/items/{item_b['id']}",
            json={"product_id": 2001, "quantity": 9, "price": "1.00"},
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        # The Item and both totals are unchanged
        resp = self.client.get(f"/orders/{order_b['order_id']}/items/{item_b['id']}")
        self.assertEqual(resp.get_json(), item_b)

        for order in (order_a, order_b):
            resp = self.client.get(f"/orders/{order['order_id']}")
            self.assertEqual(resp.get_json()["total_amount"], "21.00")

    def test_update_order_item_invalid_payload(self):
        """It should return JSON 400 for an incomplete or invalid payload"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order = self.client.post("/orders", json=payload).get_json()
        order_id = order["order_id"]
        item = order["items"][0]
        url = f"/orders/{order_id}/items/{item['id']}"

        payloads = [
            [],
            {},
            {"quantity": 1, "price": "5.25"},
            {"product_id": 1002, "price": "5.25"},
            {"product_id": 1002, "quantity": 1},
            {"product_id": "1002", "quantity": 1, "price": "5.25"},
            {"product_id": 0, "quantity": 1, "price": "5.25"},
            {"product_id": True, "quantity": 1, "price": "5.25"},
            {"product_id": 1002, "quantity": True, "price": "5.25"},
            {"product_id": 1002, "quantity": 0, "price": "5.25"},
            {"product_id": 1002, "quantity": -1, "price": "5.25"},
            {"product_id": 1002, "quantity": 1, "price": "invalid"},
            {"product_id": 1002, "quantity": 1, "price": "-1.00"},
            {"product_id": 1002, "quantity": 1, "price": "NaN"},
        ]

        for body in payloads:
            with self.subTest(payload=body):
                resp = self.client.put(url, json=body)
                self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertTrue(resp.is_json)
                self.assertEqual(resp.get_json()["error"], "Bad Request")

        # A request without a body is rejected too
        resp = self.client.put(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Nothing was changed by the rejected requests
        resp = self.client.get(url)
        self.assertEqual(resp.get_json(), item)

        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.get_json()["total_amount"], "21.00")

    def test_delete_order_item(self):
        """It should Delete an Item from an Order and recalculate the total"""
        payload = {
            "customer_id": 123,
            "items": [
                {"product_id": 1001, "quantity": 2, "price": "10.50"},
                {"product_id": 1002, "quantity": 1, "price": "5.00"},
            ],
        }

        order = self.client.post("/orders", json=payload).get_json()
        order_id = order["order_id"]
        item_id = order["items"][0]["id"]
        self.assertEqual(order["total_amount"], "26.00")

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(resp.data, b"")

        # The Item no longer exists
        resp = self.client.get(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # The parent Order remains with the other Item and an updated total
        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["product_id"], 1002)
        self.assertEqual(data["total_amount"], "5.00")

    def test_delete_last_order_item(self):
        """It should keep the Order when its only Item is deleted"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order = self.client.post("/orders", json=payload).get_json()
        order_id = order["order_id"]
        item_id = order["items"][0]["id"]

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["total_amount"], "0.00")

    def test_delete_order_item_not_found(self):
        """It should return 404 when the Item to delete does not exist"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order = self.client.post("/orders", json=payload).get_json()
        order_id = order["order_id"]
        item_id = order["items"][0]["id"]

        # An Item that never existed
        resp = self.client.delete(f"/orders/{order_id}/items/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Item with id '0' was not found", data["message"])

        # An Item that was already deleted
        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        resp = self.client.delete(f"/orders/{order_id}/items/{item_id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # The second attempt does not change the Order
        resp = self.client.get(f"/orders/{order_id}")
        self.assertEqual(resp.get_json()["total_amount"], "0.00")

    def test_delete_order_item_order_not_found(self):
        """It should return 404 when deleting an Item from an Order that does not exist"""
        resp = self.client.delete("/orders/0/items/1")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn("Order with id '0' was not found", data["message"])

    def test_delete_order_item_wrong_order(self):
        """It should not delete an Item that belongs to a different Order"""
        payload = {
            "customer_id": 123,
            "items": [{"product_id": 1001, "quantity": 2, "price": "10.50"}],
        }

        order_a = self.client.post("/orders", json=payload).get_json()
        order_b = self.client.post("/orders", json=payload).get_json()
        item_b_id = order_b["items"][0]["id"]

        resp = self.client.delete(f"/orders/{order_a['order_id']}/items/{item_b_id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.is_json)

        data = resp.get_json()
        self.assertEqual(data["error"], "Not Found")
        self.assertIn(f"Item with id '{item_b_id}' was not found", data["message"])

        # The Item is still there, and neither total changed
        resp = self.client.get(f"/orders/{order_b['order_id']}/items/{item_b_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        for order in (order_a, order_b):
            resp = self.client.get(f"/orders/{order['order_id']}")
            self.assertEqual(resp.get_json()["total_amount"], "21.00")

    def test_list_orders_by_status(self):
        """It should list only orders with the requested status"""
        pending_order = Order()
        pending_order.customer_id = 42
        pending_order.status = "pending"
        pending_order.create()

        cancelled_order = Order()
        cancelled_order.customer_id = 10
        cancelled_order.status = "cancelled"
        cancelled_order.create()

        another_pending_order = Order()
        another_pending_order.customer_id = 20
        another_pending_order.status = "pending"
        another_pending_order.create()

        resp = self.client.get("/orders?status=pending")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")

        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(order["status"] == "pending" for order in data))

    def test_list_orders_by_status_no_match(self):
        """It should return an empty list when no Orders match the status"""
        order = Order()
        order.customer_id = 42
        order.status = "pending"
        order.create()

        resp = self.client.get("/orders?status=completed")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content_type, "application/json")
        self.assertEqual(resp.get_json(), [])

    def test_list_orders_by_customer_id_and_status(self):
        """It should list orders filtered by customer_id and status"""
        order1 = Order()
        order1.customer_id = 42
        order1.status = "pending"
        order1.create()

        order2 = Order()
        order2.customer_id = 42
        order2.status = "cancelled"
        order2.create()

        order3 = Order()
        order3.customer_id = 10
        order3.status = "pending"
        order3.create()

        resp = self.client.get("/orders?customer_id=42&status=pending")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["customer_id"], 42)
        self.assertEqual(data[0]["status"], "pending")

    def test_create_order_valid_deserialize_payload(self):
        """Accept valid payload, deserialize in model and return 201 Created"""
        payload = {
            "customer_id": 200,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "20.00",
            "items": [{"product_id": 10, "quantity": 1, "price": "20.00"}],
        }
        resp = self.client.post("/orders", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["customer_id"], 200)

    def test_create_order_rejects_negative_customer_id(self):
        """POST /orders: negative customer_id triggers model validation → 400"""
        payload = {
            "customer_id": -99,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "10.00",
            "items": [],
        }
        resp = self.client.post("/orders", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.is_json)

    def test_create_order_rejects_invalid_status(self):
        """POST /orders: invalid status enum triggers model validation → 400"""
        payload = {
            "customer_id": 100,
            "order_date": "2026-10-20T12:00:00",
            "status": "wrong_status",
            "total_amount": "10.00",
            "items": [],
        }
        resp = self.client.post("/orders", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.is_json)

    def test_create_order_rejects_negative_total_amount(self):
        """POST /orders: negative total_amount triggers model validation →400"""
        payload = {
            "customer_id": 100,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "-99.00",
            "items": [],
        }
        resp = self.client.post("/orders", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.is_json)

    def test_create_order_rejects_items_not_list(self):
        """POST /orders: items is not list triggers model validation →400"""
        payload = {
            "customer_id": 100,
            "order_date": "2026-10-20T12:00:00",
            "status": "pending",
            "total_amount": "10.00",
            "items": "not-a-list",
        }
        resp = self.client.post("/orders", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.is_json)
