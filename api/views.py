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
    # def get(self, request):
    #     testcases = TestCase.objects.all()
    #     serializer = TestCaseSerializer(testcases, many=True)
    #     return Response(serializer.data)

    permission_classes = [permissions.AllowAny]
    testcases = TestCase.objects.all()
    serializer_class = TestCaseSerializer

    def list(self, request):  #called in get request
        testcases = TestCase.objects.all()
        serializer = self.serializer_class(testcases, many=True)
        return Response(serializer.data)
    
    def create(self, request):  #called in post request
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid(): 
            serializer.save()
            return Response(serializer.data)
        else: 
            return Response(serializer.errors, status=400)

    def retrieve(self, request, pk=None):
        project = self.testcases.get(pk=pk)  #the pk of the query set must be the same as the parameter in the url
        serializer = self.serializer_class(project)
        return Response(serializer.data)

    def update(self, request, pk=None): #called on put request
        project = self.testcases.get(pk=pk)
        serializer = self.serializer_class(project,data=request.data)
        if serializer.is_valid(): 
            serializer.save()
            return Response(serializer.data)
        else: 
            return Response(serializer.errors, status=400)

    def destroy(self, request, pk=None): #called on delete request
        project = self.testcases.get(pk=pk)
        project.delete()
        return Response(status=204)


class ParseStepsAPIView(APIView):

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

        if TestStepTest.objects.filter(testcase=testcase).exists():
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

                identifier_map = {
                    'ANDROID_UIAUTOMATOR': 'ANDROID_UIAUTOMATOR',
                    'CLASS_NAME': 'CLASS_NAME',
                    'ID': 'ID',
                    'XPATH': 'XPATH',
                    # Add other mappings if needed
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
                    "element_id": element_match.group("value"),
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
            TestStepTest.objects.create(
                testcase=testcase,
                step_order=i,
                element_identifier_type=step["element_identifier_type"],
                element_id=step["element_id"],
                action=step["action"],
                input_type=step.get("input_type"),
                parameter_name=step.get("parameter_name"),
                input_field_type=step.get("input_field_type"),

            )

        return Response({"message": f"{len(parsed_steps)} steps saved."}, status=201)