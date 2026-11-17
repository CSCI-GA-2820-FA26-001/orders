"""
Order Steps

Steps that load test data into the Orders service through its REST API.
"""

import os

import requests
from behave import given

HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
WAIT_TIMEOUT = 30


@given("the following orders")
def load_orders(context):
    """Delete all Orders and load new ones from the scenario table"""
    base_url = os.getenv("BASE_URL", "http://localhost:8080")
    rest_endpoint = f"{base_url}/api/orders"

    response = requests.get(rest_endpoint, timeout=WAIT_TIMEOUT)
    assert response.status_code == HTTP_200_OK
    for order in response.json():
        response = requests.delete(f"{rest_endpoint}/{order['order_id']}", timeout=WAIT_TIMEOUT)
        assert response.status_code == HTTP_204_NO_CONTENT

    for row in context.table:
        payload = {
            "customer_id": int(row["customer_id"]),
            "status": row["status"],
            "items": [],
        }
        response = requests.post(rest_endpoint, json=payload, timeout=WAIT_TIMEOUT)
        assert response.status_code == HTTP_201_CREATED
