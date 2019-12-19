from django.db import models


class TikiModel(models.Model):

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, default="")
    price = models.CharField(max_length=255, default=0)
    raw_data = models.TextField(default="")
