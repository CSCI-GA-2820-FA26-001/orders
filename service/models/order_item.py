"""
OrderItem Model

An OrderItem represents a product contained in an Order.
"""

from decimal import Decimal, InvalidOperation

from .persistent_base import db, PersistentBase, DataValidationError


######################################################################
#  O R D E R   I T E M   M O D E L
######################################################################
class OrderItem(db.Model, PersistentBase):
    """
    Class that represents an OrderItem
    """

    __tablename__ = "order_items"

    # Table Schema
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return (
            f"<OrderItem product_id={self.product_id} "
            f"id=[{self.id}] order=[{self.order_id}]>"
        )

    def serialize(self) -> dict:
        """Converts an OrderItem into a dictionary"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "price": str(self.price) if self.price is not None else None,
        }

    def deserialize(self, data: dict) -> None:
        """
        Populates an OrderItem from a dictionary

        Args:
            data (dict): A dictionary containing the OrderItem data
        """
        try:
            self.order_id = data["order_id"]
            self.product_id = data["product_id"]
            self.quantity = data["quantity"]
            self.price = Decimal(str(data["price"]))

        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error

        except KeyError as error:
            raise DataValidationError(
                "Invalid OrderItem: missing " + error.args[0]
            ) from error

        except (TypeError, ValueError, InvalidOperation) as error:
            raise DataValidationError(
                "Invalid OrderItem: body of request contained bad or no data "
                + str(error)
            ) from error
