from __future__ import absolute_import, unicode_literals
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import DesiredCapabilities
from selenium import webdriver
from logging import getLogger
import json

from crawler import celery_app


@celery_app.task(bind=True, name='crawl_web')
def crawl_web(self, url):
    logger = getLogger('django.request')

    driver = webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        desired_capabilities=DesiredCapabilities.CHROME,
    )

    print('Executing task id {0.id}, args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))

    driver.get(url)
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'shopee-search-item-result__items')))
        print("Page is ready!")
        elem = driver.find_element_by_xpath("//*")
        source_code = elem.get_attribute("innerHTML")
        response = {
            "url": url,
            "raw_data": source_code
        }
    except TimeoutException as exc:
        print("Load page took too long... Retrying in 5 seconds...")
        raise self.retry(exc=exc, countdown=5)

    logger.info(json.dumps(response))
    driver.close()
    return response


@celery_app.task(bind=True, name='parse_data')
def parse_data(self, data):
    print("============== %r", data)
