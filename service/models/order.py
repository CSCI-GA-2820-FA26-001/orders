"""
Order Model

An Order represents a customer's order containing multiple Items.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from .persistent_base import db, PersistentBase, DataValidationError
from .item import Item


######################################################################
#  O R D E R   M O D E L
######################################################################
class Order(db.Model, PersistentBase):
    """
    Class that represents an Order
    """

    __tablename__ = "orders"

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    order_date = db.Column(db.DateTime(), nullable=False, default=datetime.now)
    status = db.Column(db.String(32), nullable=False, default="created")
    total_amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    items = db.relationship(
        "Item",
        backref="order",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<Order customer_id={self.customer_id} id=[{self.id}]>"

    def serialize(self) -> dict:
        """Converts an Order into a dictionary"""
        order = {
            "id": self.id,
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

    def deserialize(self, data: dict) -> None:
        """
        Populates an Order from a dictionary

        Args:
            data (dict): A dictionary containing the order data
        """
        try:
            self.customer_id = data["customer_id"]

            if isinstance(data["order_date"], str):
                self.order_date = datetime.fromisoformat(data["order_date"])
            else:
                self.order_date = data["order_date"]

            self.status = data.get("status", "created")
            self.total_amount = Decimal(str(data["total_amount"]))

            # Handle inner list of items
            item_list = data.get("items", [])

            for json_item in item_list:
                item = Item()
                item.deserialize(json_item)
                self.items.append(item)

        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error

        except KeyError as error:
            raise DataValidationError(
                "Invalid Order: missing " + error.args[0]
            ) from error

        except (TypeError, ValueError, InvalidOperation) as error:
            raise DataValidationError(
                "Invalid Order: body of request contained bad or no data " + str(error)
            ) from error
