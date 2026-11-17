document.addEventListener("DOMContentLoaded", () => {
    const orderIdInput = document.getElementById("order-id");
    const retrieveButton = document.getElementById("retrieve-order-btn");
    const deleteButton = document.getElementById("delete-order-btn");

    const resultsMessage = document.getElementById("results-message");
    const orderDetails = document.getElementById("order-details");

    const resultOrderId = document.getElementById("result-order-id");
    const resultCustomerId = document.getElementById("result-customer-id");
    const resultStatus = document.getElementById("result-status");
    const resultOrderDate = document.getElementById("result-order-date");
    const resultTotalAmount = document.getElementById("result-total-amount");
    const orderItems = document.getElementById("order-items");


    retrieveButton.addEventListener("click", async () => {
        const orderId = orderIdInput.value.trim();

        if (!orderId) {
            orderDetails.hidden = true;
            resultsMessage.textContent = "Please enter an Order ID.";
            return;
        }

        try {
            const response = await fetch(`/api/orders/${orderId}`);

            if (!response.ok) {
                orderDetails.hidden = true;

                if (response.status === 404) {
                    resultsMessage.textContent = `Order ${orderId} was not found.`;
                } else {
                    resultsMessage.textContent = "Unable to retrieve the order.";
                }

                return;
            }

            const order = await response.json();

            resultOrderId.textContent = order.order_id;
            resultCustomerId.textContent = order.customer_id;
            resultStatus.textContent = order.status;
            resultOrderDate.textContent = order.order_date;
            resultTotalAmount.textContent = order.total_amount;

            orderItems.innerHTML = "";

            order.items.forEach((item) => {
                const itemElement = document.createElement("p");

                itemElement.textContent =
                    `Product ID: ${item.product_id}, ` +
                    `Quantity: ${item.quantity}, ` +
                    `Price: ${item.price}`;

                orderItems.appendChild(itemElement);
            });

            orderDetails.hidden = false;
            resultsMessage.textContent = "Order retrieved successfully.";
        } catch (error) {
            orderDetails.hidden = true;
            resultsMessage.textContent = "Unable to retrieve the order.";
        }
    });

    deleteButton.addEventListener("click", async () => {
        const orderId = orderIdInput.value.trim();

        if (!orderId) {
            resultsMessage.textContent = "Please enter an Order ID.";
            return;
        }

        try {
            const response = await fetch(`/api/orders/${orderId}`, {
                method: "DELETE",
            });

            if (!response.ok) {
                resultsMessage.textContent = "Unable to delete the order.";
                return;
            }

            orderDetails.hidden = true;
            resultsMessage.textContent =
                `Order ${orderId} deleted successfully.`;
            orderIdInput.value = "";
        } catch (error) {
            resultsMessage.textContent = "Unable to delete the order.";
        }
    });
    const cancelButton = document.getElementById("cancel-order-btn");

    cancelButton.addEventListener("click", async () => {
        const orderId = orderIdInput.value.trim();

        if (!orderId) {
            resultsMessage.textContent = "Please enter an Order ID.";
            return;
        }

        try {
            const response = await fetch(`/api/orders/${orderId}/cancel`, {
                method: "PUT",
            });

            if (!response.ok) {
                let message = "Unable to cancel the order.";

                if (response.status === 404) {
                    message = `Order ${orderId} was not found.`;
                } else {
                    try {
                        const error = await response.json();
                        if (error.message) {
                            message = error.message;
                        }
                    } catch (parseError) {
                        // Keep the default message when the body is not JSON
                    }
                }

                resultsMessage.textContent = message;
                return;
            }

            const order = await response.json();

            resultOrderId.textContent = order.order_id;
            resultCustomerId.textContent = order.customer_id;
            resultStatus.textContent = order.status;
            resultOrderDate.textContent = order.order_date;
            resultTotalAmount.textContent = order.total_amount;

            orderDetails.hidden = false;
            resultsMessage.textContent =
                `Order ${orderId} cancelled successfully.`;
        } catch (error) {
            resultsMessage.textContent = "Unable to cancel the order.";
        }
    });

    const statusFilter = document.getElementById("status-filter");
    const searchButton = document.getElementById("search-orders-btn");
    const searchMessage = document.getElementById("search-message");
    const searchResultsBody = document.getElementById("search-results-body");

    searchButton.addEventListener("click", async () => {
        const selectedStatus = statusFilter.value;
        const url = selectedStatus
            ? `/api/orders?status=${encodeURIComponent(selectedStatus)}`
            : "/api/orders";

        searchResultsBody.innerHTML = "";

        try {
            const response = await fetch(url);

            if (!response.ok) {
                searchMessage.textContent = "Unable to search orders.";
                return;
            }

            const orders = await response.json();

            orders.forEach((order) => {
                const row = document.createElement("tr");

                [
                    order.order_id,
                    order.customer_id,
                    order.status,
                    order.order_date,
                    order.total_amount,
                ].forEach((value) => {
                    const cell = document.createElement("td");
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                searchResultsBody.appendChild(row);
            });

            searchMessage.textContent = orders.length
                ? `${orders.length} order(s) found.`
                : "No orders found.";
        } catch (error) {
            searchMessage.textContent = "Unable to search orders.";
        }
    });
});