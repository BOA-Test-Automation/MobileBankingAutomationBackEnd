from rest_framework import serializers
from .models import Application, TestSuite

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class TestSuiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSuite
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']