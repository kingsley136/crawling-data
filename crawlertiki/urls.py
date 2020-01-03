from django.urls import path

from . import views

urlpatterns = [
    path('crawl', views.CrawlerTikiGetData.as_view())
]
