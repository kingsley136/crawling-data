# -*- coding: utf-8 -*-
from rest_framework import generics, views
from rest_framework.response import Response
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from crawlershopee.models import ShopeeModel
from crawlershopee.serializers import ShopeeModelSerializer, ShopeeModelGetSerializer

from selenium import webdriver
from requests.utils import requote_uri

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

    def crawl_detail(self, url):
        driver = webdriver.Remote(
            command_executor='http://selenium:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME,

        )
        driver.get(url)
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'qaNIZv')))
            print("Page is ready!")
        except TimeoutException:
            print("Loading took too much time!")
        try:
            name_container = driver.find_element_by_class_name("qaNIZv")
            name = name_container.find_element_by_tag_name("span").text
            price = driver.find_element_by_class_name("_3n5NQx").text
            serializer = ShopeeModelSerializer(data={
                'title': name,
                'price': price,
                'raw_data': ""
            })
            driver.close()
            yield serializer
        except Exception as e:
            print("error", e)

    def callback(self, res):
        print(res)

    def post(self, request):
        url = requote_uri("https://shopee.vn/search?keyword=" + request.POST.get('keyword'))

        from crawlershopee.tasks import crawl_web, parse_data

        crawl_web.apply_async(kwargs={'url': url}, link=parse_data.s())

        return Response({"data": "ok"})
