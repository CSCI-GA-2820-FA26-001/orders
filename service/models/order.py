"""
Order Model

An Order represents a customer's order containing multiple OrderItems.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from .persistent_base import db, PersistentBase, DataValidationError
from .order_item import OrderItem


######################################################################
#  O R D E R   M O D E L
######################################################################
class Order(db.Model, PersistentBase):
    """Class that represents an Order."""

    __tablename__ = "orders"

    VALID_STATUSES = {
        "pending",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
    }

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    status = db.Column(db.String(32), nullable=False, default="pending")
    total_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    items = db.relationship(
        "OrderItem",
        backref="order",
        passive_deletes=True,
    )

    @property
    def order_id(self):
        """Returns the public Order identifier."""
        return self.id

    def __repr__(self):
        return f"<Order customer_id={self.customer_id} order_id=[{self.order_id}]>"

    def serialize(self) -> dict:
        """Converts an Order into a dictionary."""
        order = {
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "order_date": (
                self.order_date.isoformat() if self.order_date is not None else None
            ),
            "status": self.status,
            "total_amount": (
                str(self.total_amount) if self.total_amount is not None else None
            ),
            "items": [],
        }

        for item in self.items:
            order["items"].append(item.serialize())

        return order

    @staticmethod
    def _validate_customer_id(value):
        """Validate and return the customer ID."""
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise DataValidationError(
                "Invalid Order data: customer_id must be a positive integer"
            )
        return value

    @staticmethod
    def _parse_order_date(value):
        """Parse an order date or return the default date."""
        if value is None:
            return datetime.now()

        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            raise DataValidationError(
                "Invalid Order data: order_date must be a date or ISO-format string"
            )

        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise DataValidationError(f"Invalid Order data: {error}") from error

    @classmethod
    def _validate_status(cls, value):
        """Validate and return the order status."""
        if not isinstance(value, str) or value not in cls.VALID_STATUSES:
            valid_statuses = ", ".join(sorted(cls.VALID_STATUSES))
            raise DataValidationError(
                f"Invalid Order data: status '{value}' is not valid. "
                f"Valid statuses: {valid_statuses}"
            )
        return value

    @staticmethod
    def _positive_integer(value, field):
        """Convert a value to a positive integer."""
        if isinstance(value, bool):
            raise DataValidationError(
                f"Invalid order item data: {field} must be a positive integer"
            )

        try:
            value = int(value)
        except (TypeError, ValueError) as error:
            raise DataValidationError(
                f"Invalid order item data: {field} must be a positive integer"
            ) from error

        if value <= 0:
            raise DataValidationError(
                f"Invalid order item data: {field} must be a positive integer"
            )
        return value

    @staticmethod
    def _parse_price(value):
        """Convert and validate an item price."""
        try:
            price = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation) as error:
            raise DataValidationError(
                f"Invalid order item data: price must be a valid number: {error}"
            ) from error

        if not price.is_finite() or price < Decimal("0.00"):
            raise DataValidationError(
                "Invalid order item data: price must be finite and non-negative"
            )
        return price

    @classmethod
    def _deserialize_item(cls, data):
        """Create an OrderItem from a dictionary."""
        if not isinstance(data, dict):
            raise DataValidationError("Invalid order item data: expected an object")

        try:
            product_id = data["product_id"]
            quantity = data["quantity"]
            price = data["price"]
        except KeyError as error:
            raise DataValidationError(
                f"Order item missing required field: {error.args[0]}"
            ) from error

        item = OrderItem()
        item.product_id = cls._positive_integer(product_id, "product_id")
        item.quantity = cls._positive_integer(quantity, "quantity")
        item.price = cls._parse_price(price)
        return item

    def _deserialize_items(self, item_data):
        """Populate order items and return their calculated total."""
        if not isinstance(item_data, list):
            raise DataValidationError("Invalid Order data: items must be a list")

        self.items.clear()
        calculated_total = Decimal("0.00")

        for data in item_data:
            item = self._deserialize_item(data)
            self.items.append(item)
            calculated_total += item.price * item.quantity

        return calculated_total

    @staticmethod
    def _parse_total_amount(value, calculated_total):
        """Validate a supplied total or use the calculated item total."""
        if value is None:
            return calculated_total

        try:
            total = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation) as error:
            raise DataValidationError(
                f"Invalid Order data: total_amount must be a valid number: {error}"
            ) from error

        if not total.is_finite() or total < Decimal("0.00"):
            raise DataValidationError(
                "Invalid Order data: total_amount must be finite and non-negative"
            )
        return total

    def _deserialize_customer_id(self, data: dict, partial: bool) -> None:
        """Deserialize and validate the customer ID."""
        if "customer_id" in data:
            self.customer_id = self._validate_customer_id(data["customer_id"])
        elif not partial:
            raise DataValidationError("Invalid Order: missing customer_id")

    def _deserialize_order_metadata(self, data: dict, partial: bool) -> None:
        """Deserialize the order date and status."""
        if "order_date" in data:
            self.order_date = self._parse_order_date(data["order_date"])
        elif not partial:
            self.order_date = self._parse_order_date(None)

        if "status" in data:
            self.status = self._validate_status(data["status"])
        elif not partial:
            self.status = self._validate_status("pending")

    def _deserialize_items_and_total(self, data: dict, partial: bool) -> None:
        """Deserialize items and calculate or validate the order total."""
        if "items" in data:
            calculated_total = self._deserialize_items(data["items"])
            self.total_amount = self._parse_total_amount(
                data.get("total_amount"),
                calculated_total,
            )
        elif not partial:
            calculated_total = self._deserialize_items([])
            self.total_amount = self._parse_total_amount(
                data.get("total_amount"),
                calculated_total,
            )
        elif "total_amount" in data:
            self.total_amount = self._parse_total_amount(
                data["total_amount"],
                Decimal(str(self.total_amount or "0.00")),
            )

    def deserialize(self, data: dict, partial: bool = False) -> None:
        """Populate this Order from a dictionary and validate its data."""
        if not isinstance(data, dict):
            raise DataValidationError("Invalid Order data: expected a dictionary")

        self._deserialize_customer_id(data, partial)
        self._deserialize_order_metadata(data, partial)
        self._deserialize_items_and_total(data, partial)

    @classmethod
    def find_by_order_id(cls, order_id):
        """Finds an Order by its order_id."""
        return cls.find(order_id)

    @classmethod
    def find_by_status(cls, status):
        """Returns all Orders with the specified status."""
        return cls.query.filter(cls.status == status).all()
