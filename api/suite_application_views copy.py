from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .permissions import IsManager
from .models import *
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from django.db.models import Prefetch

class SuiteApplicationsView(APIView):
    """
    Get all test suites and their test cases for a specific application
    Permission: Authenticated users only
    """
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request, application_id):
        try:
            application = get_object_or_404(Application, id=application_id)
            
            # Optimized query with prefetch_related and filtering
            test_suites = TestSuite.objects.filter(
                application=application
            ).prefetch_related(
                Prefetch('testcase_set', 
                        queryset=TestCase.objects.all().order_by('name'),
                        to_attr='ordered_test_cases')
            ).order_by('name')
            
            response_data = {
                "application": {
                    "id": application.id,
                    "name": application.name,
                    "created_at": application.created_at,
                    "updated_at": application.updated_at
                },
                "test_suites": []
            }
            
            for suite in test_suites:
                suite_data = {
                    "id": suite.id,
                    "name": suite.name,
                    "description": suite.description,
                    "created_by": suite.created_by.username,
                    "created_at": suite.created_at,
                    "updated_at": suite.updated_at,
                    "test_cases": [
                        {
                            "id": case.id,
                            "name": case.name,
                            "code": case.code,
                            "application" : case.application_id,
                            "description": case.description,
                            "created_by": case.created_by.username if case.created_by else None,
                            "created_at": case.created_at,
                            "updated_at": case.updated_at
                        }
                        for case in suite.ordered_test_cases
                    ]
                }
                response_data["test_suites"].append(suite_data)
            
            return Response(response_data, status=http_status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class SetCustomGroupView(viewsets.ViewSet):
    """
    Create a custom test group with associated test cases
    Permission: Authenticated users only
    """
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        """
        Handle POST request for /setCustomGroup
        Expected request body:
        {
            "name": "Regression Suite",
            "application_id" : 1, 
            "description": "All critical regression test cases",
            "test_cases": [1, 2, 3, 4]  # array of test case IDs
        }
        """
        try:
            # Validate required fields

            required_fields = ['name', 'application_id', 'description', 'test_cases']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {"error": f"Missing required field: {field}"},
                        status=http_status.HTTP_400_BAD_REQUEST
                    )
            
            name = request.data.get('name')
            description = request.data.get('description', '')
            application_id = request.data.get('application_id')
            test_case_ids = request.data.get('test_cases', [])
            
            if not name:
                return Response(
                    {"error": "Group name is required"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            application_id = get_object_or_404(Application, id=application_id)
            
            if not isinstance(test_case_ids, list) or len(test_case_ids) == 0:
                return Response(
                    {"error": "At least one test case ID must be provided"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Create the custom test group
            custom_group = CustomTestGroup.objects.create(
                name=name,
                application=application_id,
                description=description,
                created_by=request.user
            )

            # Create group items for each test case
            for order, test_case_id in enumerate(test_case_ids, start=1):
                try:
                    test_case = TestCase.objects.get(id=test_case_id)
                    CustomTestGroupItems.objects.create(
                        custom_group=custom_group,
                        test_case=test_case,
                        order_ingroup=order
                    )
                except TestCase.DoesNotExist:
                    # If a test case doesn't exist, skip it (or you could return an error)
                    continue

            return Response(
                {
                    "message": "Custom test group created successfully",
                    "group_id": custom_group.id,
                    "total_test_cases_added": len(test_case_ids)
                },
                status=http_status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_user_custom_groups(self, request):
        """
        Get all custom test groups created by the current user
        Returns:
        [
            {
                "id": group_id,
                "name": group_name,
                "description": group_description,
                "created_at": created_at,
                "updated_at": updated_at
            },
            ...
        ]
        """
        try:
            # Get all custom groups created by the current user
            custom_groups = CustomTestGroup.objects.filter(
                created_by=request.user
            ).order_by('-created_at')
            
            response_data = []
            
            for group in custom_groups:
                response_data.append({
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "created_at": group.created_at,
                    "updated_at": group.updated_at
                })
            
            return Response(response_data, status=http_status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_custom_group_test_cases(self, request, group_id):
        """
        Get all test cases for a specific custom test group ordered by their position in the group,
        grouped by their test suite.
        Returns:
        {
            "group_id": group_id,
            "group_name": group_name,
            "group_description": group_description,
            "test_suites": [
                {
                    "suite_id": suite_id,
                    "suite_name": suite_name,
                    "suite_description": suite_description,
                    "test_cases": [
                        {
                            "id": test_case_id,
                            "name": test_case_name,
                            "code": test_case_code,
                            "description": test_case_description,
                            "order_in_group": order_position,
                            "created_at": created_at,
                            "updated_at": updated_at
                        },
                        ...
                    ]
                },
                ...
            ]
        }
        """
        try:
            # Get the custom group or return 404
            custom_group = get_object_or_404(CustomTestGroup, id=group_id)
            
            # Get all test cases for this group ordered by their position
            group_items = CustomTestGroupItems.objects.filter(
                custom_group=custom_group
            ).select_related(
                'test_case',
                'test_case__suite',
                'test_case__application'
            ).order_by('order_ingroup')
            
            response_data = {
                "group_id": custom_group.id,
                "group_name": custom_group.name,
                "group_description": custom_group.description,
                "test_suites": []
            }
            
            # Dictionary to store suites and their test cases
            suites_dict = {}
            
            for item in group_items:
                test_case = item.test_case
                suite = test_case.suite
                
                # If suite not in dictionary, add it
                if suite.id not in suites_dict:
                    suites_dict[suite.id] = {
                        "suite_id": suite.id,
                        "suite_name": suite.name,
                        "suite_description": suite.description,
                        "application_id": suite.application.id,
                        "application_name": suite.application.name,
                        "test_cases": []
                    }
                
                # Add test case to its suite
                suites_dict[suite.id]["test_cases"].append({
                    "id": test_case.id,
                    "name": test_case.name,
                    "code": test_case.code,
                    "description": test_case.description,
                    "order_in_group": item.order_ingroup,
                    "created_at": test_case.created_at,
                    "updated_at": test_case.updated_at
                })
            
            # Convert dictionary to list for response
            response_data["test_suites"] = list(suites_dict.values())
            
            return Response(response_data, status=http_status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
                
            )
        
class AssignBatchToTesterView(APIView):
    """
    Assign a custom test group to a tester as a batch assignment
    Permission: Authenticated users only
    """
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        """
        Handle POST request for /assignBatchToTester
        Expected request body:
        {
            "name" : "Batch Name",
            "priority": "high",
            "deadline": "2023-12-31T23:59:59Z",
            "assigned_to_id": 2,  # ID of the tester being assigned
            "notes": "Please complete this by Friday",
            "custom_group_id": 10,  # ID of the custom test group
            "assignment_type_id": 1  # ID of the test type
        }
        Returns:
        {
            "message": "Batch assignment created successfully",
            "batch_id": 123,
            "total_test_cases": 15
        }
        """
        try:
            # Validate required fields
            required_fields = ['name', 'priority', 'assigned_to_id', 'custom_group_id', 'assignment_type_id']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {"error": f"Missing required field: {field}"},
                        status=http_status.HTTP_400_BAD_REQUEST
                    )

            # Get the custom group
            custom_group_id = request.data['custom_group_id']
            custom_group = get_object_or_404(CustomTestGroup, id=custom_group_id)

            # Count test cases in the custom group
            total_test_cases = CustomTestGroupItems.objects.filter(
                custom_group=custom_group
            ).count()

            if total_test_cases == 0:
                return Response(
                    {"error": "The custom test group has no test cases"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Get the test type
            assignment_type_id = request.data['assignment_type_id']
            assignment_type = get_object_or_404(TestType, id=assignment_type_id)

            # Create the batch assignment
            batch_assignment = BatchAssignment.objects.create(
                name=request.data['name'],
                assigned_by=request.user,
                assigned_to_id=request.data['assigned_to_id'],
                assignment_type=assignment_type,
                customgroup=custom_group,
                status='pending',
                notes=request.data.get('notes', ''),
                priority=request.data['priority'],
                totaltestcases=total_test_cases,
                completedtestcases=0,
                passedtestcases=0,
                deadline=request.data.get('deadline')
            )

            # Create batch assignment test case entries
            group_items = CustomTestGroupItems.objects.filter(
                custom_group=custom_group
            ).select_related('test_case')
            
            for item in group_items:
                BatchAssignmentTestCase.objects.create(
                    batch=batch_assignment,
                    test_case=item.test_case
                )

            return Response(
                {
                    "message": "Batch assignment created successfully",
                    "batch_id": batch_assignment.id,
                    "total_test_cases": total_test_cases
                },
                status=http_status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )