from django.urls import path

from . import views

urlpatterns = [
    path('', views.CrawlerTikiView.as_view()),
    path('crawl', views.CrawlerTikiGetData.as_view())
]
