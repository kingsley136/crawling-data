from rest_framework import serializers

from crawlershopee.models import ShopeeModel


class ShopeeModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopeeModel
        exclude = ('raw_data',)


class ShopeeModelGetSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShopeeModel
        exclude = ('raw_data', )
