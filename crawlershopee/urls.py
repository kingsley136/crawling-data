from django.urls import path

from . import views

urlpatterns = [
    path('crawl', views.CrawlerShopeeGetData.as_view())
]
