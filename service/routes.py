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
Orders Service with Flask-RESTX

Paths:
------
GET /health - Health check for Kubernetes
GET / - Service metadata
GET /api/orders - Returns a list of Orders
GET /api/orders/{id} - Returns an Order
POST /api/orders - Creates a new Order
PUT /api/orders/{id} - Updates an Order
DELETE /api/orders/{id} - Deletes an Order
PUT /api/orders/{id}/cancel - Cancels a pending Order
GET /api/orders/{id}/items - Lists Items in an Order
POST /api/orders/{id}/items - Adds an Item to an Order
GET /api/orders/{id}/items/{item_id} - Returns an Item
PUT /api/orders/{id}/items/{item_id} - Updates an Item
DELETE /api/orders/{id}/items/{item_id} - Deletes an Item
"""

from decimal import Decimal, InvalidOperation
from flask import jsonify
from flask import current_app as app  # Import Flask application
from flask_restx import Api, Resource, fields, reqparse
from service.common import status  # HTTP Status Codes
from service.models import Order, OrderItem


######################################################################
# Configure Swagger before initializing it
######################################################################
api = Api(
    app,
    version="1.0.0",
    title="Orders REST API Service",
    description="This is an Orders microservice for an eCommerce back end.",
    default="orders",
    default_label="Order operations",
    doc="/apidocs",
    prefix="/api",
    catch_all_404s=True,
)


######################################################################
# GET HEALTH CHECK
######################################################################
@app.route("/health")
def health():
    """Let Kubernetes know the service is running"""
    return jsonify(status="OK"), status.HTTP_200_OK


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
            list_url="/api/orders",
        ),
        status.HTTP_200_OK,
    )


# Define the models so that the docs reflect what can be sent
create_item_model = api.model(
    "OrderItemCreate",
    {
        "product_id": fields.Integer(
            required=True, description="The product identifier"
        ),
        "quantity": fields.Integer(
            required=True, description="How many of the product were ordered"
        ),
        "price": fields.String(
            required=True, description="Unit price as a decimal string"
        ),
    },
)

item_model = api.inherit(
    "OrderItemModel",
    create_item_model,
    {
        "id": fields.Integer(
            readOnly=True, description="The unique id assigned to the item"
        ),
        "order_id": fields.Integer(
            readOnly=True, description="The order this item belongs to"
        ),
    },
)

create_model = api.model(
    "Order",
    {
        "customer_id": fields.Integer(
            required=True, description="The customer that placed the order"
        ),
        "status": fields.String(
            description="Order status",
            enum=list(Order.VALID_STATUSES),
        ),
        "order_date": fields.String(
            description="ISO 8601 order date; defaults to now when omitted"
        ),
        "items": fields.List(
            fields.Nested(create_item_model),
            description="Optional list of items to create with the order",
        ),
    },
)

order_model = api.model(
    "OrderModel",
    {
        "order_id": fields.Integer(
            readOnly=True, description="The unique id assigned to the Order"
        ),
        "customer_id": fields.Integer(
            required=True, description="The customer that placed the order"
        ),
        "status": fields.String(
            description="Order status",
            enum=list(Order.VALID_STATUSES),
        ),
        "order_date": fields.String(
            description="ISO 8601 order date; defaults to now when omitted"
        ),
        "total_amount": fields.String(
            readOnly=True, description="Sum of price * quantity for all items"
        ),
        "items": fields.List(
            fields.Nested(item_model), description="Order items"
        ),
    },
)

update_order_model = api.model(
    "OrderUpdate",
    {
        "customer_id": fields.Integer(
            required=True, description="Updated customer identifier"
        ),
    },
)

# query string arguments
order_args = reqparse.RequestParser()
order_args.add_argument(
    "customer_id",
    type=str,
    location="args",
    required=False,
    help="List Orders by customer_id",
)
order_args.add_argument(
    "status",
    type=str,
    location="args",
    required=False,
    help="List Orders by status",
)


######################################################################
#  U T I L I T Y   F U N C T I O N S
######################################################################
def abort(error_code: int, message: str):
    """Logs errors before aborting"""
    app.logger.error(message)
    api.abort(error_code, message)


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


######################################################################
# PATH: /orders/{order_id}
######################################################################
@api.route("/orders/<int:order_id>")
@api.param("order_id", "The Order identifier")
class OrderResource(Resource):
    """
    OrderResource class

    Allows the manipulation of a single Order
    """

    # ------------------------------------------------------------------
    # RETRIEVE AN ORDER
    # ------------------------------------------------------------------
    @api.doc("get_orders")
    @api.response(404, "Order not found")
    @api.marshal_with(order_model)
    def get(self, order_id):
        """Retrieve a single Order"""
        app.logger.info("Request to Retrieve an order with id [%s]", order_id)

        order = Order.find_by_order_id(order_id)
        if not order:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Order with id '{order_id}' was not found.",
            )

        return order.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN EXISTING ORDER
    # ------------------------------------------------------------------
    @api.doc("update_orders")
    @api.response(404, "Order not found")
    @api.response(400, "The posted Order data was not valid")
    @api.expect(update_order_model)
    @api.marshal_with(order_model)
    def put(self, order_id):
        """Update top-level fields on an existing Order"""
        app.logger.info("Request to update Order with id [%s]", order_id)

        order = Order.find_by_order_id(order_id)
        if not order:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Order with id '{order_id}' was not found.",
            )

        data = api.payload
        if not isinstance(data, dict) or not data:
            abort(
                status.HTTP_400_BAD_REQUEST,
                "A JSON request body is required.",
            )

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

        return order.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE AN ORDER
    # ------------------------------------------------------------------
    @api.doc("delete_orders")
    @api.response(204, "Order deleted")
    def delete(self, order_id):
        """
        Delete an Order

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
# PATH: /orders
######################################################################
@api.route("/orders", strict_slashes=False)
class OrderCollection(Resource):
    """Handles all interactions with collections of Orders"""

    # ------------------------------------------------------------------
    # LIST ALL ORDERS
    # ------------------------------------------------------------------
    @api.doc("list_orders")
    @api.expect(order_args, validate=True)
    @api.marshal_list_with(order_model)
    def get(self):
        """Returns all of the Orders, optionally filtered"""
        app.logger.info("Request to List Orders")

        args = order_args.parse_args()
        customer_id = args.get("customer_id")
        order_status = args.get("status")

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
        results = [order.serialize() for order in orders]
        app.logger.info("[%s] Orders returned", len(results))
        return results, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # ADD A NEW ORDER
    # ------------------------------------------------------------------
    @api.doc("create_orders")
    @api.response(400, "The posted data was not valid")
    @api.expect(create_model)
    @api.marshal_with(order_model, code=201)
    def post(self):
        """Creates an Order"""
        app.logger.info("Request to create an Order")

        data = api.payload
        if data is None:
            abort(
                status.HTTP_400_BAD_REQUEST,
                "A JSON request body is required.",
            )

        order = Order()
        order.deserialize(data)
        order.create()

        location_url = api.url_for(
            OrderResource, order_id=order.id, _external=True
        )
        return (
            order.serialize(),
            status.HTTP_201_CREATED,
            {"Location": location_url},
        )


######################################################################
# PATH: /orders/{order_id}/cancel
######################################################################
@api.route("/orders/<int:order_id>/cancel")
@api.param("order_id", "The Order identifier")
class CancelResource(Resource):  # pylint: disable=too-few-public-methods
    """Cancel actions on an Order"""

    @api.doc("cancel_orders")
    @api.response(404, "Order not found")
    @api.response(409, "The Order cannot be cancelled")
    @api.marshal_with(order_model)
    def put(self, order_id):
        """
        Cancel an Order

        This action changes the status of a pending Order to cancelled.
        """
        app.logger.info("Request to cancel Order with id [%s]", order_id)

        order = Order.find_by_order_id(order_id)
        if not order:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Order with id '{order_id}' was not found.",
            )

        if order.status != "pending":
            abort(
                status.HTTP_409_CONFLICT,
                f"Order with id '{order_id}' is '{order.status}' and cannot be cancelled.",
            )

        order.status = "cancelled"
        order.update()

        app.logger.info("Order with id [%s] has been cancelled", order_id)
        return order.serialize(), status.HTTP_200_OK


######################################################################
# PATH: /orders/{order_id}/items
######################################################################
@api.route("/orders/<int:order_id>/items", strict_slashes=False)
@api.param("order_id", "The Order identifier")
class OrderItemCollection(Resource):
    """Handles all interactions with collections of Order Items"""

    # ------------------------------------------------------------------
    # LIST ITEMS IN AN ORDER
    # ------------------------------------------------------------------
    @api.doc("list_order_items")
    @api.response(404, "Order not found")
    @api.marshal_list_with(item_model)
    def get(self, order_id):
        """List all Items in an Order"""
        app.logger.info("Request to List items for order with id [%s]", order_id)

        order = Order.find_by_order_id(order_id)
        if not order:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Order with id '{order_id}' was not found.",
            )

        results = [item.serialize() for item in order.items]
        return results, status.HTTP_200_OK

    # ------------------------------------------------------------------
    # ADD AN ITEM TO AN ORDER
    # ------------------------------------------------------------------
    @api.doc("create_order_items")
    @api.response(404, "Order not found")
    @api.response(400, "The posted Item data was not valid")
    @api.expect(create_item_model)
    @api.marshal_with(item_model, code=201)
    def post(self, order_id):
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

        product_id, quantity_value, price = validate_item_payload(api.payload)

        item = OrderItem()
        item.product_id = product_id
        item.quantity = quantity_value
        item.price = price

        order.items.append(item)
        order.total_amount = (
            Decimal(str(order.total_amount or 0)) + price * quantity_value
        )
        order.update()

        location_url = api.url_for(
            OrderItemResource,
            order_id=order_id,
            item_id=item.id,
            _external=True,
        )
        return (
            item.serialize(),
            status.HTTP_201_CREATED,
            {"Location": location_url},
        )


######################################################################
# PATH: /orders/{order_id}/items/{item_id}
######################################################################
@api.route("/orders/<int:order_id>/items/<int:item_id>")
@api.param("order_id", "The Order identifier")
@api.param("item_id", "The Order Item identifier")
class OrderItemResource(Resource):
    """
    OrderItemResource class

    Allows the manipulation of a single Order Item
    """

    # ------------------------------------------------------------------
    # RETRIEVE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("get_order_items")
    @api.response(404, "Item not found")
    @api.marshal_with(item_model)
    def get(self, order_id, item_id):
        """Retrieve a single Item from an Order"""
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

        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # UPDATE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("update_order_items")
    @api.response(404, "Item not found")
    @api.response(400, "The posted Item data was not valid")
    @api.expect(create_item_model)
    @api.marshal_with(item_model)
    def put(self, order_id, item_id):
        """Update an item in an existing Order"""
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

        product_id, quantity, price = validate_item_payload(api.payload)

        item.product_id = product_id
        item.quantity = quantity
        item.price = price

        order.total_amount = sum(
            (order_item.price * order_item.quantity for order_item in order.items),
            Decimal("0.00"),
        )
        order.update()

        app.logger.info("Item with id [%s] has been updated", item_id)
        return item.serialize(), status.HTTP_200_OK

    # ------------------------------------------------------------------
    # DELETE AN ITEM
    # ------------------------------------------------------------------
    @api.doc("delete_order_items")
    @api.response(204, "Item deleted")
    @api.response(404, "Item not found")
    def delete(self, order_id, item_id):
        """Delete an Item from an Order"""
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

        order.total_amount = sum(
            (i.price * i.quantity for i in order.items if i.id != item.id),
            Decimal("0.00"),
        )
        item.delete()

        app.logger.info("Item with id [%s] has been deleted", item_id)
        return "", status.HTTP_204_NO_CONTENT
