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
Orders Service

This service implements the REST API for Orders.
"""

from decimal import Decimal, InvalidOperation
from flask import jsonify, request, url_for, abort
from flask import current_app as app  # Import Flask application
from service.common import status  # HTTP Status Codes
from service.models import Order, OrderItem


######################################################################
# GET INDEX
######################################################################
@app.route("/")
def index():
    """Root URL response with service metadata"""
    return (
        jsonify(
            name="Orders Service",
            version="1.0",
            list_url="/orders",
        ),
        status.HTTP_200_OK,
    )


######################################################################
#  R E S T   A P I   E N D P O I N T S
######################################################################
@app.route("/orders", methods=["POST"])
def create_order():
    """Creates a new Order"""

    app.logger.info("Request to create an Order")

    data = request.get_json(silent=True)

    # Validate request body
    if not data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "No request data was provided",
        )

    if "customer_id" not in data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "Missing required field: customer_id",
        )

    if "items" not in data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "Missing required field: items",
        )

    if not isinstance(data["items"], list) or not data["items"]:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "items must be a non-empty list",
        )

    # Create the Order
    order = Order()
    order.customer_id = data["customer_id"]
    order.status = "pending"

    # Start total at $0.00
    total_amount = Decimal("0.00")

    # Create each OrderItem
    for item_data in data["items"]:
        try:
            product_id = item_data["product_id"]
            quantity = int(item_data["quantity"])
            price = Decimal(str(item_data["price"]))

        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidOperation,
        ):
            abort(
                status.HTTP_400_BAD_REQUEST,
                "Invalid order item",
            )

        if quantity <= 0 or price < 0:
            abort(
                status.HTTP_400_BAD_REQUEST,
                "Invalid order item quantity or price",
            )

        item = OrderItem()
        item.product_id = product_id
        item.quantity = quantity
        item.price = price

        order.items.append(item)

        total_amount += price * quantity

    # Set calculated total
    order.total_amount = total_amount

    # Save Order and OrderItems
    order.create()

    # Return newly created Order
    response = jsonify(order.serialize())
    response.status_code = status.HTTP_201_CREATED
    response.headers["Location"] = f"/orders/{order.id}"

    return response


######################################################################
# LIST ORDERS
######################################################################
@app.route("/orders", methods=["GET"])
def list_orders():
    """List all Orders, optionally filtered by customer_id"""
    app.logger.info("Request to List Orders")

    customer_id = request.args.get("customer_id")

    query = Order.query

    if customer_id is not None:
        try:
            customer_id = int(customer_id)
        except ValueError:
            abort(
                status.HTTP_400_BAD_REQUEST,
                "customer_id must be an integer",
            )

        query = query.filter_by(customer_id=customer_id)

    orders = query.all()

    return (
        jsonify([order.serialize() for order in orders]),
        status.HTTP_200_OK,
    )


######################################################################
# READ AN ORDER
######################################################################
@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    """
    Retrieve a single Order

    This endpoint will return an Order based on it's id
    """
    app.logger.info("Request to Retrieve an order with id [%s]", order_id)

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    return jsonify(order.serialize()), status.HTTP_200_OK


######################################################################
# UPDATE AN ORDER
######################################################################
@app.route("/orders/<int:order_id>", methods=["PUT"])
def update_order(order_id):
    """Update top-level fields on an existing Order"""
    app.logger.info("Request to update Order with id [%s]", order_id)

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "A JSON request body is required.",
        )

    # This endpoint updates order-level data only.
    if "items" in data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "Order items must be updated through the items resource.",
        )

    if "customer_id" not in data:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "Missing required field: customer_id",
        )

    customer_id = data["customer_id"]
    if (
        not isinstance(customer_id, int)
        or isinstance(customer_id, bool)
        or customer_id <= 0
    ):
        abort(
            status.HTTP_400_BAD_REQUEST,
            "customer_id must be a positive integer",
        )

    order.customer_id = customer_id
    order.update()

    return jsonify(order.serialize()), status.HTTP_200_OK


######################################################################
# DELETE AN ORDER
######################################################################
@app.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    """
    Delete an Order

    This endpoint will delete an Order based on the id specified in the path
    """
    app.logger.info("Request to Delete an order with id [%s]", order_id)

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    order.delete()

    app.logger.info("Order with id [%s] has been deleted", order_id)
    return "", status.HTTP_204_NO_CONTENT


######################################################################
# ADD AN ITEM TO AN ORDER
######################################################################
@app.route("/orders/<int:order_id>/items", methods=["POST"])
def add_item_to_order(order_id):
    """Add an item to an existing Order"""
    app.logger.info(
        "Request to add an item to Order with id [%s]",
        order_id,
    )

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(
            status.HTTP_400_BAD_REQUEST,
            "A JSON request body is required.",
        )

    for field in ("product_id", "quantity", "price"):
        if field not in data:
            abort(
                status.HTTP_400_BAD_REQUEST,
                f"Missing required field: {field}",
            )

    product_id = data["product_id"]
    quantity_value = data["quantity"]

    if (
        not isinstance(product_id, int)
        or isinstance(product_id, bool)
        or product_id <= 0
    ):
        abort(status.HTTP_400_BAD_REQUEST, "product_id must be a positive integer")

    if (
        not isinstance(quantity_value, int)
        or isinstance(quantity_value, bool)
        or quantity_value <= 0
    ):
        abort(status.HTTP_400_BAD_REQUEST, "quantity must be a positive integer")

    try:
        price = Decimal(str(data["price"]))
    except (TypeError, ValueError, InvalidOperation):
        abort(status.HTTP_400_BAD_REQUEST, "price must be a valid number")

    if not price.is_finite() or price < 0:
        abort(status.HTTP_400_BAD_REQUEST, "price must be a non-negative number")

    item = OrderItem()
    item.product_id = product_id
    item.quantity = quantity_value
    item.price = price

    order.items.append(item)

    order.total_amount = Decimal(str(order.total_amount or 0)) + price * quantity_value

    order.update()

    response = jsonify(item.serialize())
    response.status_code = status.HTTP_201_CREATED
    response.headers["Location"] = f"/orders/{order_id}/items/{item.id}"
    return response
