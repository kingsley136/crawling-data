# -*- coding: utf-8 -*-

from rest_framework import views
from rest_framework.response import Response

from crawler.settings import ELK_HOST

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search


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
            item = {
                "categories": [category for category in hit.categories],
                "title": hit.title,
                "gross_price": {
                    "min": hit.gross_price.min,
                    "max": hit.gross_price.max
                },
                "net_price": {
                    "min": hit.net_price.min,
                    "max": hit.net_price.max
                },
                "source": hit.type,
                "url": hit.url
            }
            items.append(item)

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