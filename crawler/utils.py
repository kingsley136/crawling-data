from selenium.webdriver import DesiredCapabilities
from selenium import webdriver


def scroll_down_page(driver, speed=100):
    current_scroll_position, new_height = 0, 1
    while current_scroll_position <= new_height:
        current_scroll_position += speed
        driver.execute_script("window.scrollTo(0, {});".format(current_scroll_position))
        new_height = driver.execute_script("return document.body.scrollHeight")


def get_price(price_string):
    if '-' in price_string:
        prices = price_string.split('-')
        min_price = prices[0]
        max_price = prices[1]
        return {
            'min': int(min_price.split('₫')[0].replace('.', '').replace('đ', '')),
            'max': int(max_price.split('₫')[0].replace('.', '').replace('đ', ''))
        }
    else:
        # FIXME Optimize
        return {
            'min': int(price_string.split('₫')[0].replace('.', '').replace('đ', '')),
            'max': int(price_string.split('₫')[0].replace('.', '').replace('đ', ''))
        }


def create_driver():
    return webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        desired_capabilities=DesiredCapabilities.CHROME,
    )
