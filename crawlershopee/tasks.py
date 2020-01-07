from __future__ import absolute_import, unicode_literals

from django.core.mail import send_mail

from datetime import datetime, timedelta

from django.template.loader import render_to_string
from django.utils.html import strip_tags
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException

from logging import getLogger
from celery.utils.log import get_task_logger
from bs4 import BeautifulSoup

from crawler import celery_app
from crawler.utils import get_price, scroll_down_page, create_driver

import logging
import re

elk_logger = getLogger('django.request')

SELENIUM_DRIVER = None

# FIXME Create base class task


@celery_app.task(bind=True, name='crawl_shopee_url', max_retries=10)
def crawl_shopee_url(self, url, required_class, label, scroll_to_bottom=False):
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


@celery_app.task(bind=True, name='get_shopee_products_url')
def get_shopee_products_url(self, data):
    # Return list product url from result page crawled
    html_doc = data.get('raw_data')
    soup = BeautifulSoup(html_doc, 'html.parser')
    items_container = soup.findChild("div", {"class": "shopee-search-item-result__items"})

    item_urls = items_container.find_all('a')[:10]
    urls = []
    for item_url in item_urls:
        if re.match(r"^https?:\/\/(w{3}\.)?shopee.vn\/.*?$", item_url.get('href')):
            urls.append(item_url.get('href'))
    logging.warning("end loop...")

    from celery import chord
    chord(crawl_shopee_url.subtask(
        queue='priority.high',
        kwargs={
            'url': 'http://shopee.vn' + item_url.get('href'),
            'required_class': '_3n5NQx',
            'label': 'crawling_product_detail',
        },
        countdown=30,
        link=get_shopee_product_detail.s(),
        expires=datetime.now() + timedelta(days=1)
    ) for item_url in item_urls)(on_finish_crawl_shopee.s())

    response = {
        'search_url': data.get('url'),
        'prods_urls': urls
    }
    elk_logger.info(response)

    return response


@celery_app.task(bind=True, name='get_shopee_product_detail')
def get_shopee_product_detail(self, data):
    logging.warning("Getting product data...")
    html_doc = data.get('raw_data')
    if html_doc:
        soup = BeautifulSoup(html_doc, 'html.parser')
        categories_html = soup.findAll("a", {"class": "JFOy4z _20XOUy"})
        categories = []
        for category_html in categories_html:
            categories.append(category_html.text)
        title = soup.findChild("span", {"class": "OSgLcw"})
        gross_price = soup.findChild("div", {"class": "_3_ISdg"})
        net_price = soup.findChild("div", {"class": "_3n5NQx"})
        try:
            item_info = {
                "url": data.get('url'),
                "title": title.text.replace('\n', ''),
                "gross_price": get_price(gross_price.text) if gross_price else get_price(net_price.text),
                "net_price": get_price(net_price.text),
                "categories": categories,
                "type": "shopee",
                'task_id': self.request.root_id
            }
            elk_logger.info(msg="Saved item " + data.get('url'), extra=item_info)
            return item_info
        except AttributeError as exc:
            print("Error while parsing data, crawl again...")
            celery_app.send_task(
                "crawl_url",
                queue='priority.high',
                kwargs={
                    'url': data.get('url'),
                    'required_class': '_3n5NQx',
                    'label': 'crawling_product_detail',
                },
                countdown=30,
                link=get_shopee_product_detail.s(),
                expires=datetime.now() + timedelta(days=1)
            )
    else:
        celery_app.send_task(
            "crawl_url",
            queue='priority.high',
            kwargs={
                'url': data.get('url'),
                'required_class': '_3n5NQx',
                'label': 'crawling_product_detail',
            },
            countdown=30,
            link=get_shopee_product_detail.s(),
            expires=datetime.now() + timedelta(days=1)
        )


@celery_app.task(bind=True, name='on_finish_crawl_shopee')
def on_finish_crawl_shopee(self, data):
    driver = SELENIUM_DRIVER
    if driver:
        driver.quit()
    subject = 'Your request(#%s) finished successfully!' % self.request.root_id
    html_message = render_to_string('email_template.html', {
        'graph_url': 'http://localhost:8000/results/%s/graph' % self.request.root_id,
        'url': 'http://localhost:8000/results/%s' % self.request.root_id
    })
    plain_message = strip_tags(html_message)
    from_email = 'no_reply@2code.io'
    to_email = 'khtrinh.tran@gmail.com'

    send_mail(
        subject,
        plain_message,
        from_email,
        [to_email],
        html_message=html_message,

    )

