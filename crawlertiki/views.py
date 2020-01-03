# -*- coding: utf-8 -*-
import ast

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


class CrawlResult(views.APIView):

    def get(self, request, *args, **kwargs):
        # FIXME try to use django-rest-elasticsearch instead
        page = int(request.GET.get('page')) if request.GET.get('page') else 0
        limit = int(request.GET.get('limit')) if request.GET.get('limit') else 20
        task_id = kwargs.get('task_id')
        client = Elasticsearch(hosts=[ELK_HOST + ':9200'], http_auth=('elastic', 'L5M3LPXk6QhxTyZenwo5'))

        s = Search(
            using=client,
            index="logstash*"
        ).filter("match", task_id=task_id)[(page * limit): (page * limit + limit)]

        elk_response = s.execute()
        items = []
        total = elk_response.hits.total
        for hit in elk_response:
            items.append(ast.literal_eval(hit.message))

        return Response({
            'total': total.value,
            'limit': limit,
            'next': '' if (
                    (page * limit + limit) > total.value
            ) else (
                    "http://%s%s?page=%s&limit=%s" %
                    (request.META.get('HTTP_HOST'), request.META.get('PATH_INFO'), page + 1, limit)
            ),
            'items': items
        })
