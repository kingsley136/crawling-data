from rest_framework import serializers

from crawlertiki.models import TikiModel


class TikiModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = TikiModel
        fields = "__all__"
