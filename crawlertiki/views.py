# -*- coding: utf-8 -*-

from rest_framework import views
from rest_framework.response import Response

from crawler.settings import ELK_HOST

from crawlertiki.tasks import craw_tiki_url, get_tiki_products_url

from requests.utils import requote_uri

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search


class CrawlerTikiGetData(views.APIView):

    def post(self, request):
        url = requote_uri("https://tiki.vn/search?q=" + request.POST.get('keyword'))

        task = craw_tiki_url.apply_async(
            kwargs={
                'url': url,
                'required_class': 'product-box-list',
                'scroll_to_bottom': False,
                'label': 'tiki_crawling_search_result',
            },
            link=get_tiki_products_url.s()
        )

        return Response({"task_id": task.id})

