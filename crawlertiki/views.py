# -*- coding: utf-8 -*-

from rest_framework import generics, views
from rest_framework.response import Response

from crawlertiki.models import TikiModel
from crawlertiki.serializers import TikiModelSerializer, TikiModelGetSerializer

import requests
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


class CrawlerTikiView(generics.ListAPIView):

    queryset = TikiModel.objects.all()
    serializer_class = TikiModelGetSerializer


class CrawlerTikiGetData(views.APIView):

    def crawl_web(self, initial_url):
        crawled, to_crawl = [], []
        to_crawl.append(initial_url)

        while to_crawl and len(crawled) < 100:
            current_url = to_crawl.pop(0)
            r = requests.get(current_url)
            crawled.append(current_url)

            serializer = TikiModelSerializer(data={
                'title': getTitle(r.text),
                'price': getPrice(r.text),
                'raw_data': str(r.content)
            })

            for url in re.findall('href="([^"]*p[0-9]+\.html[^"]*)"', str(r.text)):
                pattern = re.compile('https?')
                if pattern.match(url) and url not in crawled:
                    to_crawl.append(url)
            yield serializer

    def post(self, request):
        crawl_web_generator = self.crawl_web('https://tiki.vn/dien-thoai-smartphone/c1795?src=tree&_lc=Vk4wMzkwMjIwMTM%3D')
        for serializer in crawl_web_generator:
            if serializer.is_valid():
                serializer.save()
        return Response({"data": "ok"})
