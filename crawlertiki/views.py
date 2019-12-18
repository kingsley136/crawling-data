from rest_framework import generics, views
from rest_framework.response import Response

from crawlertiki.models import TikiModel
from crawlertiki.serializers import TikiModelSerializer

import requests
import re


class CrawlerTikiView(generics.ListAPIView):

    queryset = TikiModel.objects.all()
    serializer_class = TikiModelSerializer


class CrawlerTikiGetData(views.APIView):

    def crawl_web(self, initial_url):
        crawled, to_crawl = [], []
        to_crawl.append(initial_url)

        while to_crawl:
            current_url = to_crawl.pop(0)
            r = requests.get(current_url)
            crawled.append(current_url)
            for url in re.findall('href="([^"]*p[0-9]+\.html[^"]*)"', str(r.content)):
                pattern = re.compile('https?')
                if pattern.match(url) and url != current_url:
                    to_crawl.append(url)
            yield current_url

    def post(self, request):
        crawl_web_generator = self.crawl_web('https://tiki.vn/dien-thoai-smartphone/c1795?src=tree&_lc=Vk4wMzkwMjIwMTM%3D')
        for res in crawl_web_generator:
            print(res)
        return Response({"data": "ok"})
