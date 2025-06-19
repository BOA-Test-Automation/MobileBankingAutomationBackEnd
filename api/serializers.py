from rest_framework import serializers
from .models import *


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name']

class TestSuiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSuite
        fields = ['id', 'name', 'description']

class TestCaseSerializer(serializers.ModelSerializer):
    application = ApplicationSerializer(read_only=True)
    suite = TestSuiteSerializer(read_only=True)
    application_id = serializers.IntegerField(write_only=True)
    suite_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TestCase
        fields = [
            'id', 'code', 'name', 'description',
            'application', 'suite',  # Read-only nested representations
            'application_id', 'suite_id',  # Write-only IDs
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class TestStepTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStepTest
        fields = ['id', 'action', 'name']

class RerunStepSerializer(serializers.ModelSerializer):

    Code = serializers.CharField(source='testcase.code', read_only=True)
    Name = serializers.CharField(source='testcase.name', read_only=True)
    ElementId = serializers.CharField(source='element_id', read_only=True)
    Action = serializers.CharField(source='action', read_only=True)
    
    ElementIdentifier = serializers.CharField(source='element_identifier_type.name', read_only=True)

    class Meta:
        model = TestStep
        fields = ['id', 'Code', 'Name', 'ElementId', 'Action', 'ElementIdentifier']