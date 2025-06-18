from rest_framework import serializers
from .models import *

class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ['id', 'code', 'name']


class TestStepTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStepTest
        fields = ['id', 'action', 'name']