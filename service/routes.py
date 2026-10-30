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
from flask import jsonify, request, abort
from flask import current_app as app  # Import Flask application
from service.common import status  # HTTP Status Codes
from service.models import Order, OrderItem, DataValidationError


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
#  REST API ENDPOINTS
######################################################################
@app.route("/orders", methods=["POST"])
def create_order():
    """Create a new Order."""
    app.logger.info("Request to create an Order")

    data = request.get_json(silent=True)

    if data is None:
        abort(
            status.HTTP_400_BAD_REQUEST,
            "A JSON request body is required.",
        )

    try:
        order = Order()
        order.deserialize(data)
        order.create()
    except DataValidationError as error:
        abort(status.HTTP_400_BAD_REQUEST, str(error))

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
    order_status = request.args.get("status")

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

    if order_status is not None:
        query = query.filter_by(status=order_status)

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
    """Update top‑level fields on an existing Order"""
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

    # This endpoint updates order‑level data only.
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

    This endpoint will delete an Order based on the id specified in the path.
    DELETE is idempotent: returns 204 whether or not the Order exists.
    """
    app.logger.info("Request to Delete an order with id [%s]", order_id)

    order = Order.find_by_order_id(order_id)
    if order:
        order.delete()
        app.logger.info("Order with id [%s] has been deleted", order_id)
    else:
        app.logger.info(
            "Order with id [%s] was not found; returning 204 (idempotent)",
            order_id,
        )

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
        abort(status.HTTP_400_BAD_REQUEST, "price must be a non‑negative number")

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


######################################################################
# LIST ITEMS IN AN ORDER
######################################################################
@app.route("/orders/<int:order_id>/items", methods=["GET"])
def list_order_items(order_id):
    """
    List all Items in an Order

    This endpoint will return all OrderItems that belong to the specified Order
    """
    app.logger.info("Request to List items for order with id [%s]", order_id)

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    results = [item.serialize() for item in order.items]
    return jsonify(results), status.HTTP_200_OK


######################################################################
# READ AN ITEM FROM AN ORDER
######################################################################
@app.route("/orders/<int:order_id>/items/<int:item_id>", methods=["GET"])
def get_order_item(order_id, item_id):
    """
    Retrieve a single Item from an Order

    This endpoint will return an OrderItem based on its id and the id of its Order
    """
    app.logger.info(
        "Request to Retrieve item with id [%s] from order with id [%s]",
        item_id,
        order_id,
    )

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    item = OrderItem.find(item_id)
    if not item or item.order_id != order.id:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Item with id '{item_id}' was not found in Order '{order_id}'.",
        )

    return jsonify(item.serialize()), status.HTTP_200_OK


######################################################################
# UPDATE AN ITEM IN AN ORDER
######################################################################
def validate_item_payload(data):
    """
    Validates the payload of an Order Item request

    Aborts with 400_BAD_REQUEST if the payload is incomplete or invalid.
    Returns the validated (product_id, quantity, price).
    """
    if not isinstance(data, dict):
        abort(status.HTTP_400_BAD_REQUEST, "A JSON request body is required.")

    for field in ("product_id", "quantity", "price"):
        if field not in data:
            abort(status.HTTP_400_BAD_REQUEST, f"Missing required field: {field}")

    product_id = data["product_id"]
    quantity = data["quantity"]

    if (
        not isinstance(product_id, int)
        or isinstance(product_id, bool)
        or product_id <= 0
    ):
        abort(status.HTTP_400_BAD_REQUEST, "product_id must be a positive integer")

    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        abort(status.HTTP_400_BAD_REQUEST, "quantity must be a positive integer")

    try:
        price = Decimal(str(data["price"]))
    except (TypeError, ValueError, InvalidOperation):
        abort(status.HTTP_400_BAD_REQUEST, "price must be a valid number")

    if not price.is_finite() or price < 0:
        abort(status.HTTP_400_BAD_REQUEST, "price must be a non‑negative number")

    return product_id, quantity, price


@app.route("/orders/<int:order_id>/items/<int:item_id>", methods=["PUT"])
def update_order_item(order_id, item_id):
    """Update an item in an existing Order."""
    app.logger.info(
        "Request to Update item with id [%s] in order with id [%s]",
        item_id,
        order_id,
    )

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    item = OrderItem.find(item_id)
    if not item or item.order_id != order.id:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Item with id '{item_id}' was not found in Order '{order_id}'.",
        )

    product_id, quantity, price = validate_item_payload(
        request.get_json(silent=True)
    )

    item.product_id = product_id
    item.quantity = quantity
    item.price = price

    order.total_amount = sum(
        (order_item.price * order_item.quantity for order_item in order.items),
        Decimal("0.00"),
    )
    order.update()

    app.logger.info("Item with id [%s] has been updated", item_id)
    return jsonify(item.serialize()), status.HTTP_200_OK



######################################################################
# DELETE AN ITEM FROM AN ORDER
######################################################################
@app.route("/orders/<int:order_id>/items/<int:item_id>", methods=["DELETE"])
def delete_order_item(order_id, item_id):
    """
    Delete an Item from an Order

    This endpoint will delete an OrderItem based on its id and the id of its Order
    """
    app.logger.info(
        "Request to Delete item with id [%s] from order with id [%s]",
        item_id,
        order_id,
    )

    order = Order.find_by_order_id(order_id)
    if not order:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Order with id '{order_id}' was not found.",
        )

    item = OrderItem.find(item_id)
    if not item or item.order_id != order.id:
        abort(
            status.HTTP_404_NOT_FOUND,
            f"Item with id '{item_id}' was not found in Order '{order_id}'.",
        )

    # Updating the total before the delete commits both in one transaction
    order.total_amount = sum(
        (i.price * i.quantity for i in order.items if i.id != item.id),
        Decimal("0.00"),
    )
    item.delete()

    app.logger.info("Item with id [%s] has been deleted", item_id)
    return "", status.HTTP_204_NO_CONTENT
