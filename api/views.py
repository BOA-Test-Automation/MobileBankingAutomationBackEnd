import re
from django.http import HttpResponse
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import *

class TestCaseListView(viewsets.ViewSet):
    
    permission_classes = [permissions.AllowAny]
    queryset = TestCase.objects.select_related('application', 'suite', 'created_by').all()
    serializer_class = TestCaseSerializer

    def list(self, request):
        serializer = self.serializer_class(self.queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            # Handle the created_by field automatically
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            serializer = self.serializer_class(testcase)
            return Response(serializer.data)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=404)

    def update(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            serializer = self.serializer_class(testcase, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=404)

    def destroy(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            testcase.delete()
            return Response(status=204)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=404)


class ParseStepsAPIView(APIView):

    def clean_element_id(self, element_id):
        """Remove escaped quotes from element IDs"""
        return element_id.replace('\\"', '"')

    def post(self, request):
        testcase_id = request.data.get("testcase_id")
        row_record = request.data.get("row_record")

        if not testcase_id or not row_record:
            return Response({"error": "Missing testcase_id or row_record"}, status=400)

        try:
            testcase = TestCase.objects.get(id=testcase_id)
        except TestCase.DoesNotExist:
            return Response({"error": "Invalid TestCase ID"}, status=404)

        # Clear existing steps
        # TestStepTest.objects.filter(testecase=testcase).delete()

        if TestStep.objects.filter(testcase=testcase).exists():
            return Response(
                {"error": f"TestCase '{testcase.name}' already has test steps. Editing is not yet supported. Please choose a different test case."},
                status=409)

        element_lines = row_record.splitlines()
        temp_elements = {}
        parsed_steps = []

        element_pattern = re.compile(
            r'(?P<el>el\d+)\s*=\s*driver\.find_element\(by=AppiumBy\.(?P<identifier>[A-Z_]+),\s*value="(?P<value>(?:\\.|[^"\\])*)"\)'
        )
        action_pattern = re.compile(
            r'(?P<el>el\d+)\.(?P<action>click|send_keys|swipe)\(?("?[^"]*"?\)?)?'
        )

        for line in element_lines:
            line = line.strip()
            element_match = element_pattern.search(line)
            action_match = action_pattern.search(line)

            if element_match:
                el = element_match.group("el")
                identifier = element_match.group("identifier")

                # temp_elements[el] = {
                #     "element_id": element_match.group("value"),
                #     "identifier_type": element_match.group("identifier"),
                # }

                raw_value = element_match.group("value")
                cleaned_value = self.clean_element_id(raw_value)

                identifier_map = {
                    'ANDROID_UIAUTOMATOR': 'ANDROID_UIAUTOMATOR',
                    'CLASS_NAME': 'CLASS_NAME',
                    'ID': 'ID',
                    'XPATH': 'XPATH',
                    'ACCESSIBILITY_ID': 'ACCESSIBILITY_ID'
                }

                try:
                    identifier_type = ElementIdentifierType.objects.get(
                        name=identifier_map.get(identifier, identifier)
                    )
                except ElementIdentifierType.DoesNotExist:
                    return Response(
                        {"error": f"Unsupported identifier type: {identifier}"},
                        status=400
                    )

                temp_elements[el] = {
                    "element_id": cleaned_value,
                    "element_identifier_type": identifier_type,
                }

            if action_match:
                el = action_match.group("el")
                action = action_match.group("action")
                if el in temp_elements:
                    step_data = {
                        "element_id": temp_elements[el]["element_id"],
                        "element_identifier_type": temp_elements[el]["element_identifier_type"],
                        "action": action
                    }

                    if action == "send_keys":
                        step_data["input_type"] = "dynamic"
                        step_data["parameter_name"] = "Phone Number"  
                        step_data["input_field_type"] = "text"

                    parsed_steps.append(step_data)

        for i, step in enumerate(parsed_steps, 1):
            TestStep.objects.create(
                testcase=testcase,
                step_order=i,
                element_identifier_type=step["element_identifier_type"],
                element_id=step["element_id"],
                action=step["action"],
                input_type=step.get("input_type"),
                parameter_name=step.get("parameter_name"),
                input_field_type=step.get("input_field_type"),)

        return Response({"message": f"{len(parsed_steps)} steps saved."}, status=201)

class RerunDataHandler(APIView):
    
    def get(self, request, testcase_id):
        # testcase_id = request.data.get("testcase_id")

        if not testcase_id:
            return Response({"error": "testcase_id is required in the URL."}, status=400)

        try:
            testcase = TestCase.objects.get(id=testcase_id)
        except TestCase.DoesNotExist:
            return Response({"error": "TestCase not found."}, status=404)

        steps = TestStep.objects.filter(testcase=testcase).select_related("element_identifier_type").order_by("step_order")

        data = []
        for step in steps:
            data.append({
                "ID": step.id,
                "Code": testcase.code,
                "Name": testcase.name,
                "ElementId": step.element_id,
                "Action": step.action,
                "ElementIdentifier": step.element_identifier_type.name if step.element_identifier_type else None
            })
        
        return Response({
            "data": data}, status=200)



