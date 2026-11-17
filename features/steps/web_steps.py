import os

from behave import then, when
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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
