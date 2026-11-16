from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def before_scenario(context, scenario):
    options = Options()

    # Use Chromium installed in the pipeline-selenium container
    options.binary_location = "/usr/bin/chromium"

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    service = Service("/usr/bin/chromedriver")

    context.browser = webdriver.Chrome(
        service=service,
        options=options,
    )


def after_scenario(context, scenario):
    browser = getattr(context, "browser", None)
    if browser:
        browser.quit()
