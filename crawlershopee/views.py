# -*- coding: utf-8 -*-

from rest_framework import generics, views
from rest_framework.response import Response
from selenium.webdriver import DesiredCapabilities

from crawlershopee.models import ShopeeModel
from crawlershopee.serializers import ShopeeModelSerializer, ShopeeModelGetSerializer

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import pandas as pd

import re


def getTitle(text):
    title_container_re = re.compile(
        '<h1 class="item-name" itemprop="name" id="product-name">(.*?)</h1>',
        re.IGNORECASE | re.DOTALL
    )
    title_re = re.compile('<span>(.*)</span>', re.IGNORECASE | re.DOTALL)
    title_container = re.findall(title_container_re, str(text))

    title = re.findall(title_re, str(title_container))

    return title[0] if len(title) > 0 else None


def getPrice(text):
    price_re = re.compile('<span id="span-price">(.*)</span>', re.IGNORECASE)
    price = re.findall(price_re, str(text))
    return price[0] if len(price) > 0 else None


class CrawlerShopeeView(generics.ListAPIView):

    queryset = ShopeeModel.objects.all()
    serializer_class = ShopeeModelGetSerializer


class CrawlerShopeeGetData(views.APIView):

    def post(self, request):
        driver = webdriver.Remote(
            #  Set to: htttp://{selenium-container-name}:port/wd/hub
            #  In our example, the container is named `selenium`
            #  and runs on port 4444
            command_executor='http://selenium:4444/wd/hub',
            # Set to CHROME since we are using the Chrome container
            desired_capabilities=DesiredCapabilities.CHROME,

        )
        for page in range(1, 10):

            url = "http://quotes.toscrape.com/js/page/" + str(page) + "/"

            driver.get(url)

            items = len(driver.find_elements_by_class_name("quote"))

            total = []
            for item in range(items):
                quotes = driver.find_elements_by_class_name("quote")
                for quote in quotes:
                    quote_text = quote.find_element_by_class_name('text').text
                    author = quote.find_element_by_class_name('author').text
                    new = ((quote_text, author))
                    total.append(new)
            df = pd.DataFrame(total, columns=['quote', 'author'])
            df.to_csv('quoted.csv')
        driver.close()
        return Response({"data": "ok"})
