# -*- coding: utf-8 -*-
import ast

from rest_framework import views
from rest_framework.response import Response

from crawler.settings import ELK_HOST

from crawlershopee.tasks import crawl_shopee_url, get_shopee_products_url

from requests.utils import requote_uri

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search


class CrawlerShopeeGetData(views.APIView):

    def post(self, request):
        url = requote_uri("https://shopee.vn/search?keyword=" + request.POST.get('keyword'))

        task = crawl_shopee_url.apply_async(
            kwargs={
                'url': url,
                'required_class': 'shopee-search-item-result__item',
                'scroll_to_bottom': True,
                'label': 'shopee_crawling_search_result',
            },
            link=get_shopee_products_url.s()
        )

        return Response({"task_id": task.id})
