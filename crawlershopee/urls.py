from django.urls import path, re_path

from . import views

urlpatterns = [
    path('crawl', views.CrawlerShopeeGetData.as_view()),
    re_path(r'^results/(?P<task_id>.+)?$', views.CrawlResult.as_view())
]
