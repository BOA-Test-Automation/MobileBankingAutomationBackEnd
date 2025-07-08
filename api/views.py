import re
from django.http import HttpResponse
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import IsAuthenticated
from .serializers import MyTokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, TokenError
from django.contrib.auth import authenticate
from .utils.permissions import role_required
from .permissions import IsAdmin, IsTester
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError
from django.db.utils import DataError
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from .models import *


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = UserSerializer
    # permission_classes = [IsAuthenticated]  # Optional: Add role permission if needed

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.username == 'superadmin':
            return Response({"error": "Cannot delete superadmin"}, status=403)
        return super().destroy(request, *args, **kwargs)

class TestCaseListView(viewsets.ViewSet):

    permission_classes = [IsAuthenticated, IsAdmin]  
    queryset = TestCase.objects.select_related('application', 'suite', 'created_by').all()
    serializer_class = TestCaseSerializer
    
    def list(self, request):
        serializer = self.serializer_class(self.queryset, many=True)
        return Response(serializer.data)
    
    # def create(self, request):
    #     serializer = self.serializer_class(data=request.data)
    #     if serializer.is_valid():
    #         # Handle the created_by field automatically
    #         serializer.save(created_by=request.user)
    #         return Response(serializer.data, status=200)
    #     return Response(serializer.errors, status=400)
    

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(created_by=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                error_msg = str(e)
                if 'Duplicate entry' in error_msg or 'UNIQUE constraint failed' in error_msg:
                    return Response(
                        {"error": "A TestCase with this code, name, suite, and application already exists."},
                        status=status.HTTP_409_CONFLICT
                    )
                if 'foreign key constraint fails' in error_msg or 'a foreign key constraint fails' in error_msg:
                    return Response(
                        {"error": "Invalid suite_id or application_id."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                return Response({"error": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            serializer = self.serializer_class(testcase)
            return Response(serializer.data)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=404)

    # def update(self, request, pk=None):
    #     print("Hello")
    #     try:
    #         testcase = self.queryset.get(pk=pk)
    #         serializer = self.serializer_class(testcase, data=request.data, partial=True)
    #         if serializer.is_valid():
    #             serializer.save()
    #             return Response(serializer.data)
    #         return Response(serializer.errors, status=400)
    #     except TestCase.DoesNotExist:
    #         return Response({"error": "Test case not found"}, status=404)


    def update(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            serializer = self.serializer_class(testcase, data=request.data, partial=True)
            if serializer.is_valid():
                try:
                    serializer.save()
                    return Response(serializer.data)
                except IntegrityError as e:
                    error_msg = str(e)
                    if 'Duplicate entry' in error_msg or 'UNIQUE constraint failed' in error_msg:
                        return Response(
                            {"error": "Update would create a duplicate TestCase with the same code, name, suite, and application."},
                            status=status.HTTP_409_CONFLICT
                        )
                    if 'foreign key constraint fails' in error_msg or 'a foreign key constraint fails' in error_msg:
                        return Response(
                            {"error": "Invalid suite_id or application_id."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    return Response({"error": error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=status.HTTP_404_NOT_FOUND)


    def destroy(self, request, pk=None):
        try:
            testcase = self.queryset.get(pk=pk)
            testcase.delete()
            return Response(status=200)
        except TestCase.DoesNotExist:
            return Response({"error": "Test case not found"}, status=404)
        

class ParseStepsAPIView(APIView):

    def clean_element_id(self, element_id):
        return element_id.replace('\\"', '"')

    # permission_classes = [IsAuthenticated, IsAdmin]  
    def post(self, request):
        testcase_id = request.data.get("testcase_id")
        # row_record = request.data.get("row_record")
        recorded_actions = request.data.get("recorded_actions")  # <-- New key for structured

        if not testcase_id or (not recorded_actions):
            return Response({"error": "Missing testcase_id or data"}, status=400)

        try:
            testcase = TestCase.objects.get(id=testcase_id)
        except TestCase.DoesNotExist:
            return Response({"error": "Invalid TestCase ID"}, status=404)

        if TestStepTest.objects.filter(testcase=testcase).exists():
            return Response({"error": "TestCase already has steps."}, status=409)

        parsed_steps = []

        # # Handle structured JSON format
        if recorded_actions:
            element_map = {}
            for action in recorded_actions:
                action_raw = action.get("action", "").lower()

                action_map = {
                    "findandassign": "findAndAssign",
                    "click": "click",
                    "sendkeys": "send_keys",
                    "send_keys": "send_keys",
                } 

                params = action.get("params", [])

                normalized_action = action_map.get(action_raw)

                if normalized_action == "findAndAssign":
                    by_flag, value, el = params[:3]
                    by_flag = by_flag.strip().replace("-", "").lower()  # Normalize
                    identifier_map = {
                        "android uiautomator": "ANDROID_UIAUTOMATOR",
                        "id": "ID",
                        "class name": "CLASS_NAME",
                        "xpath": "XPATH",
                        "accessibility id": "ACCESSIBILITY_ID"
                    }
                    identifier_type = identifier_map.get(by_flag)
                    if not identifier_type:
                        return Response({"error": f"Unsupported by: {by_flag}"}, status=400)

                    try:
                        identifier_obj = ElementIdentifierType.objects.get(name=identifier_type)
                    except ElementIdentifierType.DoesNotExist:
                        return Response({"error": f"Unsupported identifier: {identifier_type}"}, status=400)

                    element_map[el] = {
                        "element_id": value,
                        "element_identifier_type": identifier_obj
                    }

                elif normalized_action in ("click", "send_keys"):
                    el = params[0]
                    if el in element_map:
                        step_data = {
                            "element_id": element_map[el]["element_id"],
                            "element_identifier_type": element_map[el]["element_identifier_type"],
                            "action": normalized_action
                        }

                        if normalized_action == "send_keys":
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

        return Response({"message": f"{(recorded_actions)} steps saved."}, status=200)

class TestConnectionAPIView(APIView):

    def get(self, request):
      return Response({"message": "Hello"}, status=200)

class RefreshAccessTokenView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({"error": "Refresh token missing"}, status=400)

        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
        except TokenError:
            return Response({"error": "Invalid refresh token"}, status=401)

        response = Response({"message": "Access refreshed"})
        response.set_cookie("access_token", new_access, httponly=True, samesite="Lax")
        return response

class RerunDataHandler(APIView):
    
    # permission_classes = [IsAuthenticated] 

    def get(self, request, testcase_id):
        # testcase_id = request.data.get("testcase_id")

        if not testcase_id:
            return Response({"error": "testcase_id is required in the URL."}, status=400)

        try:
            testcase = TestCase.objects.get(id=testcase_id)
        except TestCase.DoesNotExist:
            return Response({"error": "TestCase not found."}, status=404)

        steps = TestStepTest.objects.filter(testcase=testcase).select_related("element_identifier_type").order_by("step_order")

        data = []
        for step in steps:
            data.append({
                "ID": step.id,
                "Code": testcase.code,
                "Name": testcase.name,
                "Step_order": step.step_order,
                "ElementId": step.element_id,
                "Action": step.action,
                "ElementIdentifier": step.element_identifier_type.name if step.element_identifier_type else None,
                "InputType": step.input_type,
                "LabelName": step.parameter_name,
                "InputFieldType" : step.input_field_type,
                "ActualInput" : step.actual_input,
                "TestCase_id" : step.testcase_id
            })
        
        return Response({
            "rerundata": data}, status=200)

class CookieTokenObtainView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({"error": "Invalid credentials"}, status=401)

        refresh = RefreshToken.for_user(user)
        response = Response({
            "role": user.role,
            "username": user.username
        })
        response.set_cookie("access_token", str(refresh.access_token), httponly=True, samesite="Lax")
        response.set_cookie("refresh_token", str(refresh), httponly=True, samesite="Lax")
        return response

class Loginview(APIView):
    def post(self, request):
        email = request.data["email"]
        password = request.data["password"]
        print("Received from React", email, password)
        
        try:
            user = User.objects.get(email = email)
        except User.DoesNotExist:
            raise AuthenticationFailed("Account does  not exist")

        if user is None:
            raise AuthenticationFailed("User does not exist")
        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect Password")
        access_token = str(AccessToken.for_user(user))
        refresh_token = str(RefreshToken.for_user(user))
        return Response({
            "access_token" : access_token,
            "refresh_token" : refresh_token
        })
    
class CheckAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Authenticated"})
       
class LogoutView(APIView):
        def post(self, request):
            response = Response({"message": "Logged out successfully"})
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

class ApplicationWithSuitesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationWithSuitesSerializer
    # permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class TestAdminView(APIView):
  
  permission_classes = [IsAuthenticated, IsAdmin]  

  def post(self, request):
      return Response({"message": "Hello Admin! 👋"})
  
class StartTestExecution(APIView):

    # permission_classes = [IsAuthenticated, IsTester]

    def post(self, request):
        test_case_id = request.data.get("test_case_id")
        assignment_id = request.data.get("assignment_id")
        device_uuid = request.data.get("device_uuid")
        device_name = request.data.get("device_name")
        os_version = request.data.get("os_version")
        platform = request.data.get("platform", "Android")  # Default to Android

        if not all([test_case_id, device_uuid, assignment_id, os_version, platform]):
            return Response(
                {"error": "Requird fields are missing"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        test_case = get_object_or_404(TestCase, id=test_case_id)

        # try:
        #     test_case = TestCase.objects.get(id=test_case_id)
        # except TestCase.DoesNotExist:
        #     return Response(
        #         {"error": "Test case not found"},
        #         status=status.HTTP_404_NOT_FOUND
        #     )

        try:
            device, created = Device.objects.get_or_create(
                device_uuid=device_uuid,
                defaults={
                    'device_name' : device_name,
                    'platform': platform,
                    'os_version': os_version
                }
            )

            test_execution = TestExecution.objects.create(
                test_case=test_case,
                executed_by=request.user,
                executed_device=device,
                overallstatus='in_progress'
            )

            if assignment_id:
                try:
                    assignment = TestAssignment.objects.get(
                        id=assignment_id,
                        assigned_to=request.user  
                    )
                    
                    if not assignment.execution:
                        assignment.execution = test_execution
                        assignment.status = 'in_progress'
                        assignment.save()
                    else:
                        print(f"TestAssignment {assignment_id} already has execution {assignment.execution.id}")
                except TestAssignment.DoesNotExist:
                        print(f"TestAssignment {assignment_id} not found or doesn't belong to user {request.user.id}")

            response_data = {
                "message": "Test execution initialized successfully",
                "test_execution_id": test_execution.id,
                "assignment_updated": bool(assignment_id),  
                "device_id": device.id,
                "device_created": created,
                "status": "in_progress",
                "timestamp": timezone.now().isoformat()
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Failed to initialize test execution: {str(e)}")
            return Response(
                {"error": f"Failed to initialize test execution: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        #     response_data = {
        #         "message": "Test execution initialized successfully",
        #         "test_execution_id": test_execution.id,
        #         "device_id": device.id,
        #         "device_created": created,
        #         "status": "in_progress",
        #         "timestamp": timezone.now().isoformat()
        #     }

        #     return Response(response_data, status=status.HTTP_201_CREATED)

        # except Exception as e:
        #     return Response(
        #         {"error": f"Failed to initialize test execution: {str(e)}"},
        #         status=status.HTTP_500_INTERNAL_SERVER_ERROR
        #     )