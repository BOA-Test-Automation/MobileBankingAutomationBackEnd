from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import TestCase, TestStepTest
from .serializers import TestCaseSerializer
import re

class TestCaseListView(APIView):
    def get(self, request):
        testcases = TestCase.objects.all()
        serializer = TestCaseSerializer(testcases, many=True)
        return Response(serializer.data)


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
        TestStepTest.objects.filter(testecase=testcase).delete()

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
                temp_elements[el] = {
                    "element_id": element_match.group("value"),
                    "identifier_type": element_match.group("identifier"),
                }

            if action_match:
                el = action_match.group("el")
                action = action_match.group("action")
                if el in temp_elements:
                    parsed_steps.append({
                        "element_id": temp_elements[el]["element_id"],
                        "identifier_type": temp_elements[el]["identifier_type"],
                        "action": action,
                    })

        for i, step in enumerate(parsed_steps, 1):
            TestStepTest.objects.create(
                testecase=testcase,
                step_order=i,
                identifier_type=step["identifier_type"],
                element_id=step["element_id"],
                action=step["action"]
            )

        return Response({"message": f"{len(parsed_steps)} steps saved."}, status=201)