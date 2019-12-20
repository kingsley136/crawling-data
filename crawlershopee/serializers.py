from rest_framework import serializers

from crawlershopee.models import ShopeeModel


class ShopeeModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopeeModel
        fields = "__all__"


class ShopeeModelGetSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopeeModel
        exclude = ('raw_data', )
