# -*- coding: utf-8 -*-
import logging

from plotly.offline import plot
from rest_framework import views
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from crawler.settings import ELK_HOST

from elasticsearch import Elasticsearch, RequestError
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Match
import plotly.express as px


class CrawResultBase(object):

    def get_elk_response(self, request, task_id):
        # FIXME try to use django-rest-elasticsearch instead
        page = int(request.GET.get('page')) if request.GET.get('page') else 0
        limit = int(request.GET.get('limit')) if request.GET.get('limit') else 20
        if request.GET.get('order'):
            field, order = request.GET.get('order').split(',')
            sort_option = {
                field: {
                    "order": order
                }
            }
        else:
            sort_option = {}
        client = Elasticsearch(hosts=[ELK_HOST + ':9200'], http_auth=('elastic', 'L5M3LPXk6QhxTyZenwo5'))

        s = Search(
            using=client,
            index="logstash*"
        ).query(
            "match",
            task_id=task_id
        )
        if request.GET.get('category'):
            s = s.query(
                Match(
                    categories={
                        "query": request.GET.get('category')
                    }
                )
            )

        s = s.sort(
            sort_option
        )[(page * limit): (page * limit + limit)]

        try:
            elk_response = s.execute()
        except RequestError as exc:
            logging.warning(exc)
            return Response({
                "Message": "Wrong query!"
            })
        return elk_response, limit, page

    def parse_elk_response(self, elk_response):

        total = elk_response.hits.total
        items = []
        for hit in elk_response:
            item = {
                "categories": [category for category in hit.categories],
                "name": hit.title,
                "gross_price": {
                    "min": hit.gross_price.min,
                    "max": hit.gross_price.max
                },
                "net_price": {
                    "min": hit.net_price.min,
                    "max": hit.net_price.max
                },
                "price": hit.net_price.min,
                "source": hit.type,
                "url": hit.url
            }
            items.append(item)
        return items, total


class CrawlResult(views.APIView, CrawResultBase):

    def get(self, request, *args, **kwargs):

        elk_response, limit, page = self.get_elk_response(request, kwargs.get('task_id'))
        items, total = self.parse_elk_response(elk_response)
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


class CrawlGraphResult(views.APIView, CrawResultBase):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'result.html'

    def get(self, request, *args, **kwargs):
        elk_response, limit, page = self.get_elk_response(request, kwargs.get('task_id'))
        items, total = self.parse_elk_response(elk_response)
        plot_div = 'No data'
        if len(items) > 0:
            df = items
            fig = px.line(df, x="name", y="price", title='Task %s' % kwargs.get('task_id'))
            plot_div = plot(fig, output_type='div', include_plotlyjs=True)
        return Response({
            'graph': plot_div
        })
