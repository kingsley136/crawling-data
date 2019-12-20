from django.urls import path

from . import views

urlpatterns = [
    path('', views.CrawlerShopeeView.as_view()),
    path('crawl', views.CrawlerShopeeGetData.as_view())
]
