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
