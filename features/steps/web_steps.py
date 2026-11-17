import os

from behave import then, when
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


@when("I visit the home page")
def visit_home_page(context):
    base_url = os.getenv("BASE_URL", "http://localhost:8080")
    context.browser.get(base_url)


@then("I should see the Orders administration page")
def verify_admin_home_page(context):
    heading = WebDriverWait(context.browser, 10).until(
        EC.presence_of_element_located((By.ID, "page-title"))
    )

    assert heading.text == "Orders Service Administration"


@when('I enter "{order_id}" as the Order ID')
def enter_order_id(context, order_id):
    order_id_field = WebDriverWait(context.browser, 10).until(
        EC.presence_of_element_located((By.ID, "order-id"))
    )
    order_id_field.clear()
    order_id_field.send_keys(order_id)


@when("I click the Delete Order button")
def click_delete_order(context):
    delete_button = WebDriverWait(context.browser, 10).until(
        EC.element_to_be_clickable((By.ID, "delete-order-btn"))
    )
    delete_button.click()


@then('I should see the message "{message}"')
def verify_message(context, message):
    WebDriverWait(context.browser, 10).until(
        EC.text_to_be_present_in_element(
            (By.ID, "results-message"),
            message,
        )
    )

    results_message = context.browser.find_element(
        By.ID,
        "results-message",
    )

    assert results_message.text == message


@when('I select "{value}" in the Status filter')
def select_status_filter(context, value):
    """Select a value in the Status filter dropdown"""
    status_filter = WebDriverWait(context.browser, 10).until(
        EC.presence_of_element_located((By.ID, "status-filter"))
    )
    Select(status_filter).select_by_value(value)


@when("I click the Search Orders button")
def click_search_orders(context):
    """Click the Search Orders button"""
    search_button = WebDriverWait(context.browser, 10).until(
        EC.element_to_be_clickable((By.ID, "search-orders-btn"))
    )
    search_button.click()


@then('I should see the search message "{message}"')
def verify_search_message(context, message):
    """Check the search results message"""
    WebDriverWait(context.browser, 10).until(
        EC.text_to_be_present_in_element((By.ID, "search-message"), message)
    )
    search_message = context.browser.find_element(By.ID, "search-message")
    assert search_message.text == message


@then("I should see {count:d} orders in the search results")
def verify_search_result_count(context, count):
    """Check how many orders appear in the search results"""
    rows = context.browser.find_elements(By.CSS_SELECTOR, "#search-results-body tr")
    assert len(rows) == count, f"Expected {count} rows, found {len(rows)}"


@then('I should only see orders with status "{order_status}" in the search results')
def verify_search_result_status(context, order_status):
    """Check that every search result has the given status"""
    cells = context.browser.find_elements(By.CSS_SELECTOR, "#search-results-body tr td:nth-child(3)")
    assert cells, "Expected at least one order in the search results"
    for cell in cells:
        assert cell.text == order_status, f"Found order with status '{cell.text}'"
