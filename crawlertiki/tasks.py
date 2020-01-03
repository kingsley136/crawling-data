from __future__ import absolute_import, unicode_literals

from django.core.mail import send_mail

from datetime import datetime, timedelta

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import DesiredCapabilities
from selenium import webdriver

from logging import getLogger
from celery.utils.log import get_task_logger
from bs4 import BeautifulSoup

import logging
import time

from crawler import celery_app

elk_logger = getLogger('django.request')

celery_logger = get_task_logger(__name__)


def create_driver():
    return webdriver.Remote(
        command_executor='http://selenium:4444/wd/hub',
        desired_capabilities=DesiredCapabilities.CHROME,
    )


SELENIUM_DRIVER = None


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


@celery_app.task(bind=True, name='get_product_detail')
def get_product_detail(self, data):
    logging.warning("Getting product data...")
    html_doc = data.get('raw_data')
    if html_doc:
        soup = BeautifulSoup(html_doc, 'html.parser')
        categories_container = soup.findChild("ul", {"class": "breadcrumb"})
        categories = []
        for category in categories_container.find_all("a"):
            categories.append(category.text)

        title = soup.findChild("h1", {"id": "product-name"})
        gross_price = soup.findChild("span", {"id": "span-list-price"})
        net_price = soup.findChild("span", {"id": "span-price"})
        try:
            item_info = {
                "url": data.get('url'),
                "title": title.text.replace('\n', ''),
                "gross_price": get_price(gross_price.text) if gross_price else get_price(net_price.text),
                "net_price": get_price(net_price.text),
                "categories": categories
            }
            elk_logger.info(msg=item_info, extra={
                'task_id': self.request.root_id
            })
            return item_info
        except AttributeError as exc:
            print("Error while parsing data, crawl again...")
            celery_app.send_task(
                "crawl_url",
                queue='priority.high',
                kwargs={
                    'url': data.get('url'),
                    'required_class': 'item-name',
                    'label': 'tiki_crawling_product_detail',
                },
                countdown=30,
                link=get_product_detail.s(),
                expires=datetime.now() + timedelta(days=1)
            )

    else:
        celery_app.send_task(
            "crawl_url",
            queue='priority.high',
            kwargs={
                'url': data.get('url'),
                'required_class': 'item-name',
                'label': 'tiki_crawling_product_detail',
            },
            countdown=30,
            link=get_product_detail.s(),
            expires=datetime.now() + timedelta(days=1)
        )


@celery_app.task(bind=True, name='on_finish')
def on_finish(self, data):
    driver = SELENIUM_DRIVER
    if driver:
        driver.quit()
    send_mail(
        'Crawl website successfully',
        'Please go to http://localhost:8000/tiki/results/%s to see list items' % self.request.root_id,
        'from@example.com',
        ['khtrinh.tran@gmail.com'],
        fail_silently=False,
    )


@celery_app.task(bind=True, name='get_products_url')
def get_products_url(self, data):
    # Return list product url from result page crawled
    html_doc = data.get('raw_data')
    soup = BeautifulSoup(html_doc, 'html.parser')
    items_container = soup.findChild("div", {"class": "product-box-list"})
    time.sleep(5)
    item_urls = items_container.find_all('a')[:1]
    urls = []
    for item_url in item_urls:
        urls.append(item_url.get('href'))
    logging.warning("end loop...")

    from celery import chord
    chord(crawl_url.subtask(
        queue='priority.high',
        kwargs={
            'url': item_url.get('href'),
            'required_class': 'item-name',
            'label': 'tiki_crawling_product_detail',
        },
        countdown=30,
        link=get_product_detail.s(),
        expires=datetime.now() + timedelta(days=1)
    ) for item_url in item_urls)(on_finish.s())

    response = {
        'search_url': data.get('url'),
        'prods_urls': urls
    }
    elk_logger.info(response)

    return response


@celery_app.task(bind=True, name='crawl_url', max_retries=10)
def crawl_url(self, url, required_class, label, scroll_to_bottom=False):
    global SELENIUM_DRIVER
    logging.warning('Executing task id {0.id}, args: {0.args!r} kwargs: {0.kwargs!r}'.format(self.request))

    try:
        if SELENIUM_DRIVER:
            driver = SELENIUM_DRIVER
        else:
            SELENIUM_DRIVER = create_driver()
            driver = SELENIUM_DRIVER
        driver.get(url)
    except WebDriverException as exc:
        SELENIUM_DRIVER = create_driver()
        print("Chrome not reachable")
        raise self.retry(exc=exc, countdown=10)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, required_class)))
        logging.warning("Page is ready! Start crawling...")
        if scroll_to_bottom:
            logging.warning("Scrolling to bottom...")
            scroll_down_page(driver)
        logging.warning("Page crawled successfully")
        source_code = driver.page_source
        response = {
            "url": url,
            "label": label,
            "raw_data": source_code
        }
    except TimeoutException as exc:
        logging.warning("Load page took too long... Retrying in 5 seconds...")
        raise self.retry(exc=exc, countdown=10)
    except WebDriverException as exc:
        logging.warning("Error while crawling %r... retrying...", url)
        raise self.retry(exc=exc, countdown=10)

    elk_logger.info(response)
    return response
