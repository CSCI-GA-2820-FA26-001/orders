from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def before_scenario(context, scenario):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    context.browser = webdriver.Chrome(options=options)


def after_scenario(context, scenario):
    browser = getattr(context, "browser", None)
    if browser:
        browser.quit()
