from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from .permissions import IsTester
from .permissions import IsManager
from .models import *
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from django.db.models import Prefetch
from django.db.models import Case, When, Value, IntegerField
from rest_framework import status

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
    Create and manage custom test groups with associated test cases
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
            
            application = get_object_or_404(Application, id=application_id)
            
            if not isinstance(test_case_ids, list) or len(test_case_ids) == 0:
                return Response(
                    {"error": "At least one test case ID must be provided"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Create the custom test group
            custom_group = CustomTestGroup.objects.create(
                name=name,
                application=application,
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

    def get_edit_custom_group_data(self, request, group_id):
        """
        Get data for editing a custom test group
        Returns:
        {
            "group": {
                "id": group_id,
                "name": group_name,
                "description": group_description,
                "application_id": application_id
            },
            "test_suites": [
                {
                    "id": suite_id,
                    "name": suite_name,
                    "test_cases": [
                        {
                            "id": test_case_id,
                            "name": test_case_name,
                            "selected": boolean,
                            "order_in_group": order_position (if selected)
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
            custom_group = get_object_or_404(
                CustomTestGroup, 
                id=group_id,
                created_by=request.user  # Only creator can edit
            )
            
            # Get all test cases in this group
            group_test_cases = set(
                CustomTestGroupItems.objects.filter(
                    custom_group=custom_group
                ).values_list('test_case_id', flat=True)
            )
            
            # Get group items with order information
            group_items = {
                item.test_case_id: item.order_ingroup 
                for item in CustomTestGroupItems.objects.filter(
                    custom_group=custom_group
                )
            }
            
            # Get all test suites and test cases for the application
            test_suites = TestSuite.objects.filter(
                application=custom_group.application
            ).prefetch_related(
                Prefetch('testcase_set', 
                        queryset=TestCase.objects.all().order_by('name'),
                        to_attr='ordered_test_cases')
            ).order_by('name')
            
            response_data = {
                "group": {
                    "id": custom_group.id,
                    "name": custom_group.name,
                    "description": custom_group.description,
                    "application_id": custom_group.application.id
                },
                "test_suites": []
            }
            
            for suite in test_suites:
                suite_data = {
                    "id": suite.id,
                    "name": suite.name,
                    "test_cases": []
                }
                
                for case in suite.ordered_test_cases:
                    is_selected = case.id in group_test_cases
                    case_data = {
                        "id": case.id,
                        "name": case.name,
                        "selected": is_selected
                    }
                    if is_selected:
                        case_data["order_in_group"] = group_items[case.id]
                    
                    suite_data["test_cases"].append(case_data)
                
                response_data["test_suites"].append(suite_data)
            
            return Response(response_data, status=http_status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_custom_group(self, request, group_id):
        """
        Update a custom test group with new test cases
        Expected request body:
        {
            "name": "Updated Group Name",
            "description": "Updated description",
            "test_cases": [1, 2, 3, 4]  # array of test case IDs in desired order
        }
        """
        try:
            # Get the custom group or return 404
            custom_group = get_object_or_404(
                CustomTestGroup, 
                id=group_id,
                created_by=request.user  # Only creator can edit
            )
            
            # Validate required fields
            if 'test_cases' not in request.data:
                return Response(
                    {"error": "test_cases field is required"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            test_case_ids = request.data.get('test_cases', [])
            
            if not isinstance(test_case_ids, list):
                return Response(
                    {"error": "test_cases must be an array"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            # Update group metadata if provided
            if 'name' in request.data:
                custom_group.name = request.data['name']
            if 'description' in request.data:
                custom_group.description = request.data['description']
            custom_group.save()
            
            # Delete all existing group items
            CustomTestGroupItems.objects.filter(custom_group=custom_group).delete()
            
            # Create new group items in the specified order
            for order, test_case_id in enumerate(test_case_ids, start=1):
                try:
                    test_case = TestCase.objects.get(id=test_case_id)
                    CustomTestGroupItems.objects.create(
                        custom_group=custom_group,
                        test_case=test_case,
                        order_ingroup=order
                    )
                except TestCase.DoesNotExist:
                    # Skip invalid test case IDs
                    continue
            
            return Response(
                {
                    "message": "Custom test group updated successfully",
                    "group_id": custom_group.id,
                    "total_test_cases": len(test_case_ids)
                },
                status=http_status.HTTP_200_OK
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
                    # "order_in_group": item.order_ingroup,
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
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        try:
            # Validate required fields
            required_fields = ['name', 'priority', 'assigned_to_id']
            if not all(field in request.data for field in required_fields):
                return Response(
                    {"error": "Missing required fields: name, priority, assigned_to_id"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine assignment type and source
            if 'custom_group_id' in request.data:
                assignment_type_name = 'Custom_Group'
                custom_group = get_object_or_404(CustomTestGroup, id=request.data['custom_group_id'])
                total_test_cases = CustomTestGroupItems.objects.filter(
                    custom_group=custom_group
                ).count()
                source_field = 'customgroup'
                source = custom_group
            elif 'application_id' in request.data:
                assignment_type_name = 'Application'
                application = get_object_or_404(Application, id=request.data['application_id'])
                total_test_cases = TestCase.objects.filter(application=application).count()
                source_field = 'application'
                source = application
            elif 'suite_id' in request.data:
                assignment_type_name = 'Suite'
                suite = get_object_or_404(TestSuite, id=request.data['suite_id'])
                total_test_cases = TestCase.objects.filter(suite=suite).count()
                source_field = 'suite'
                source = suite
            else:
                return Response(
                    {"error": "Either custom_group_id, application_id, or suite_id must be provided"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if total_test_cases == 0:
                return Response(
                    {"error": "No test cases found for this assignment"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get or create the test type
            assignment_type, _ = TestType.objects.get_or_create(name=assignment_type_name)

            # Create batch assignment
            batch_assignment = BatchAssignment.objects.create(
                name=request.data['name'],
                assigned_by=request.user,
                assigned_to_id=request.data['assigned_to_id'],
                assignment_type=assignment_type,
                **{source_field: source},
                status='pending',
                notes=request.data.get('notes', ''),
                priority=request.data['priority'],
                totaltestcases=total_test_cases,
                completedtestcases=0,
                passedtestcases=0,
                deadline=request.data.get('deadline')
            )

            # For custom groups, create BatchAssignmentTestCase entries
            if source_field == 'customgroup':
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
                    "total_test_cases": total_test_cases,
                    "assignment_type": assignment_type_name,
                    "assignment_source": source_field
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            if 'batch_assignment' in locals():
                batch_assignment.delete()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

class TesterAssignedBatchTestsView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request):
        try:
            # Get all batch assignments for the current user
            batch_assignments = BatchAssignment.objects.filter(
                assigned_to=request.user
            ).exclude(  # Add this exclude clause
                status__in=['passed', 'failed']
            ).select_related(
                'assigned_by',
                'assignment_type',
                'customgroup',
                'application'
            ).prefetch_related(
                'batchassignmenttestcase_set__test_case'
            ).order_by('-created_at')
            
            results = []
            for batch in batch_assignments:
                # Initialize test_case_ids
                test_case_ids = []
                
                if batch.assignment_type.name == "Custom_Group":
                    # Get test cases from BatchAssignmentTestCase for Custom_Group assignments
                    test_case_ids = list(batch.batchassignmenttestcase_set.all()
                                       .values_list('test_case_id', flat=True))
                elif batch.assignment_type.name == "Application":
                    # Get all test cases for this application from TestCase table
                    if batch.application:
                        test_case_ids = list(TestCase.objects.filter(
                            application=batch.application
                        ).values_list('id', flat=True))
                
                results.append({
                    "batch_id": batch.id,
                    "batch_name": batch.name,
                    "assigned_by": batch.assigned_by.username,
                    "assigned_date": batch.created_at,
                    "priority": batch.priority,
                    "status": batch.status,
                    "deadline": batch.deadline,
                    "notes": batch.notes,
                    "assignment_type": batch.assignment_type.name if batch.assignment_type else None,
                    "total_test_cases": batch.totaltestcases,
                    "completed_test_cases": batch.completedtestcases,
                    "passed_test_cases": batch.passedtestcases,
                    "application_id": batch.application.id if batch.application else None,
                    "custom_group_id": batch.customgroup.id if batch.customgroup else None,
                    "test_case_ids": test_case_ids  # Array of test case IDs
                })

            return Response({
                "count": len(results),
                "results": results
            }, status=200)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=400
            )
        

class ManagerAssignedBatchTestsView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        try:
            # Get all batch assignments for the current user
            batch_assignments = BatchAssignment.objects.filter(
                assigned_by=request.user
            ).exclude(
                status__in=['passed', 'failed']
            ).select_related(
                'assigned_to',
                'assignment_type',
                'customgroup',
                'customgroup__application',  # Add this for custom group application access
                'application',
                'suite',
                'suite__application'  # Add this for suite application access
            ).prefetch_related(
                'batchassignmenttestcase_set__test_case'
            ).order_by('-created_at')
            
            results = []
            for batch in batch_assignments:
                # Initialize test_case_ids and application info
                test_case_ids = []
                application_id = None
                application_name = None
                
                # Determine application info based on assignment type
                if batch.assignment_type.name == "Custom_Group" and batch.customgroup:
                    application_id = batch.customgroup.application.id
                    application_name = batch.customgroup.application.name
                    # Get test cases from BatchAssignmentTestCase
                    test_case_ids = list(batch.batchassignmenttestcase_set.all()
                                       .values_list('test_case_id', flat=True))
                elif batch.assignment_type.name == "Application" and batch.application:
                    application_id = batch.application.id
                    application_name = batch.application.name
                    # Get all test cases for this application
                    test_case_ids = list(TestCase.objects.filter(
                        application=batch.application
                    ).values_list('id', flat=True))
                elif batch.assignment_type.name == "Suite" and batch.suite:
                    application_id = batch.suite.application.id
                    application_name = batch.suite.application.name
                    # Get all test cases for this suite
                    test_case_ids = list(TestCase.objects.filter(
                        suite=batch.suite
                    ).values_list('id', flat=True))
                
                results.append({
                    "batch_id": batch.id,
                    "batch_name": batch.name,
                    "assigned_to": batch.assigned_to.username,
                    "assigned_date": batch.created_at,
                    "priority": batch.priority,
                    "status": batch.status,
                    "deadline": batch.deadline,
                    "notes": batch.notes,
                    "assignment_type": batch.assignment_type.name,
                    "total_test_cases": batch.totaltestcases,
                    "completed_test_cases": batch.completedtestcases,
                    "passed_test_cases": batch.passedtestcases,
                    "application_id": application_id,
                    "application_name": application_name,  # Added application name
                    "custom_group_id": batch.customgroup.id if batch.customgroup else None,
                    "suite_id": batch.suite.id if batch.suite else None,  # Added suite ID
                    "test_case_ids": test_case_ids
                })

            return Response({
                "count": len(results),
                "results": results
            }, status=200)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=400
            )


class BatchTestCasesView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request, batch_id):
        try:
            # Get the batch assignment with related data
            batch = get_object_or_404(
                BatchAssignment.objects.select_related(
                    'assignment_type',
                    'customgroup',
                    'application',
                    'suite'  # Added suite
                ),
                id=batch_id,
                assigned_to=request.user
            )

            # Initialize variables
            test_cases_data = []
            custom_group = batch.customgroup
            application = batch.application
            suite = batch.suite  # Added suite

            # Get test cases based on assignment type
            if custom_group:
                # Custom Group logic (existing implementation)
                batch_test_cases = BatchAssignmentTestCase.objects.filter(
                    batch=batch
                ).select_related(
                    'test_case',
                    'execution'
                ).annotate(
                    order_in_group=Case(
                        When(
                            test_case__customtestgroupitems__custom_group=custom_group,
                            then='test_case__customtestgroupitems__order_ingroup'
                        ),
                        default=Value(99999),
                        output_field=IntegerField()
                    )
                ).order_by('order_in_group', 'test_case__name')

                # Get unique test cases while preserving order
                seen_test_case_ids = set()
                
                for batch_test_case in batch_test_cases:
                    test_case = batch_test_case.test_case
                    
                    if test_case.id in seen_test_case_ids:
                        continue
                    seen_test_case_ids.add(test_case.id)

                    test_cases_data.append(self._prepare_test_case_data(test_case, batch_test_case))

            elif application:
                # Application logic - get all test cases ordered by suite_id then name
                test_cases = TestCase.objects.filter(
                    application=application
                ).select_related('suite') \
                 .order_by('suite__id', 'name')

                for test_case in test_cases:
                    test_cases_data.append(self._prepare_test_case_data(test_case, None))

            elif suite:
                # Suite logic - get all test cases for the suite ordered by name
                test_cases = TestCase.objects.filter(
                    suite=suite
                ).select_related('suite') \
                 .order_by('name')

                for test_case in test_cases:
                    test_cases_data.append(self._prepare_test_case_data(test_case, None))

            else:
                return Response(
                    {"error": "Batch assignment has no valid assignment source (custom group, application, or suite)"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            response_data = {
                "batch_id": batch.id,
                "batch_name": batch.name,
                "test_type": batch.assignment_type.name,
                "batch_status": batch.status,
                "priority": batch.priority,
                "notes": batch.notes,
                "custom_group_id": custom_group.id if custom_group else None,
                "custom_group_name": custom_group.name if custom_group else None,
                "application_id": application.id if application else None,
                "application_name": application.name if application else None,
                "suite_id": suite.id if suite else None,  # Added suite info
                "suite_name": suite.name if suite else None,  # Added suite info
                "test_cases": test_cases_data,
                "count": len(test_cases_data)
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _prepare_test_case_data(self, test_case, batch_test_case):
        """Helper method to prepare test case data with dynamic steps"""
        dynamic_steps = []
        test_steps = TestStepTest.objects.filter(
            testcase=test_case,
            input_field_type='dynamic'
        ).order_by('step_order')
        
        for step in test_steps:
            dynamic_steps.append({
                "step_id": step.id,
                "step_order": step.step_order,
                "action": step.action,
                "input_type": step.input_type,
                "input_field_type": step.input_field_type,
                "parameter_name": step.parameter_name,
                "element_id": step.element_id
            })

        return {
            "testcase": test_case.name,
            "testcase_id": test_case.id,
            "code": test_case.code,
            "suite_id": test_case.suite.id,  # Include suite ID in response
            "suite_name": test_case.suite.name,  # Include suite name in response
            "status": batch_test_case.batch.status if batch_test_case else 'pending',
            "execution_id": batch_test_case.execution.id if batch_test_case and batch_test_case.execution else None,
            "description": test_case.description,
            "created_at": test_case.created_at,
            "updated_at": test_case.updated_at,
            "has_dynamic_steps": len(dynamic_steps) > 0,
            "dynamic_test_steps": dynamic_steps if dynamic_steps else None
        }
    

class GetCustomGroupTypeView(APIView):
    def get(self, request):
        try:
            # Get all test types ordered by name
            test_types = TestType.objects.all()
            
            # Prepare response data
            test_types_data = [{
                "id": test_type.id,
                "name": test_type.name,
                "created_at": test_type.created_at,
                "updated_at": test_type.updated_at
            } for test_type in test_types]

            return Response({
                "count": len(test_types_data),
                "results": test_types_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
