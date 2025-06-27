from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import *


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name']

class TestSuiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSuite
        fields = ['id', 'name', 'description', 'application_id']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data['role'],
        )
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
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


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.profile.role  # Assuming you have `Profile` with `role`
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.profile.role  # Include in response
        return data
    

class RerunStepSerializer(serializers.ModelSerializer):

    Code = serializers.CharField(source='testcase.code', read_only=True)
    Name = serializers.CharField(source='testcase.name', read_only=True)
    ElementId = serializers.CharField(source='element_id', read_only=True)
    Action = serializers.CharField(source='action', read_only=True)
    
    ElementIdentifier = serializers.CharField(source='element_identifier_type.name', read_only=True)
    

    class Meta:
        model = TestStep
        fields = ['id', 'Code', 'Name', 'ElementId', 'Action', 'ElementIdentifier']



# serializers.py
class ApplicationWithSuitesSerializer(serializers.ModelSerializer):
    suites = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ['id', 'name', 'created_at', 'updated_at', 'created_by', 'suites']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_suites(self, obj):
        suites = TestSuite.objects.filter(application=obj.id)
        return TestSuiteSerializer(suites, many=True).data
    

