from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status  # Renamed import to avoid conflict
from rest_framework.permissions import IsAuthenticated
from .models import TestAssignment, TestCase, User
from .permissions import *
from django.shortcuts import get_object_or_404
from django.utils import timezone

class TaskAssignmentView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        """
        Assign a test case to a tester
        Expected POST data:
        {
            "test_case_id": 1,
            "tester_id": 3,
            "notes": "Please test this thoroughly",
            "priority": "high",
            "deadline": "2023-12-31T23:59:59Z"
        }
        """
        test_case_id = request.data.get('test_case_id')
        tester_id = request.data.get('tester_id')
        manager_id = request.user.id
        notes = request.data.get('notes', '')
        priority = request.data.get('priority', 'medium')
        deadline_str = request.data.get('deadline')
        assignment_status = 'pending'

        # Validate required fields
        if not all([test_case_id, tester_id]):
            return Response(
                {"error": "test_case_id and tester_id are required"},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        try:
            # Parse deadline if provided
            deadline = None
            if deadline_str:
                deadline = timezone.datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                deadline_date = deadline.date()  # Extract date part only

            # Get the objects
            test_case = get_object_or_404(TestCase, id=test_case_id)
            tester = get_object_or_404(User, id=tester_id)
            manager = get_object_or_404(User, id=manager_id)
            
            # Verify roles
            if tester.role != 'tester':
                return Response(
                    {"error": "Assigned user must be a tester"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
            
            if manager.role != 'manager':
                return Response(
                    {"error": "Assigning user must be a manager"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

            # Check for existing pending assignment with same parameters
            existing_assignments = TestAssignment.objects.filter(
                test_case=test_case,
                assigned_by=manager,
                assigned_to=tester,
                status='pending',
                priority=priority
            )

            # Compare date part of deadline if exists
            if deadline:
                existing_assignments = existing_assignments.filter(
                    deadline__date=deadline_date
                )
            else:
                existing_assignments = existing_assignments.filter(
                    deadline__isnull=True
                )

            if existing_assignments.exists():
                existing_assignment = existing_assignments.first()
                return Response(
                    {
                        "error": "This test case is already assigned to the tester with identical parameters",
                        "existing_assignment_id": existing_assignment.id,
                        "assigned_date": existing_assignment.created_at,
                        "current_status": existing_assignment.status
                    },
                    status=http_status.HTTP_409_CONFLICT
                )

            # Create the assignment
            assignment = TestAssignment.objects.create(
                test_case=test_case,
                assigned_by=manager,
                assigned_to=tester,
                notes=notes,
                priority=priority,
                deadline=deadline_str,  # Store original string
                status=assignment_status
            )

            return Response(
                {
                    "message": "Test case assigned successfully",
                    "assignment_id": assignment.id,
                    "assigned_by": manager.username,
                    "assigned_to": tester.username,
                    "test_case": test_case.name,
                    "status": assignment_status
                },
                status=http_status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=http_status.HTTP_400_BAD_REQUEST
            )

class TesterAssignmentsView(APIView):
    permission_classes = [IsAuthenticated, IsTester]

    def get(self, request):
        """
        Get all assignments for the current user (tester)
        """
        if request.user.role != 'tester':
            return Response(
                {"error": "Only testers can view their assignments"},
                status=http_status.HTTP_403_FORBIDDEN
            )

        assignments = TestAssignment.objects.filter(
            assigned_to=request.user
        ).exclude(  # Add this exclude clause
                status__in=['completed_pass', 'completed_fail']
        ).select_related('test_case', 'assigned_by')

        data = []
        for assignment in assignments:
            data.append({
                "id": assignment.id,
                "test_case": {
                    "id": assignment.test_case.id,
                    "name": assignment.test_case.name,
                    "code": assignment.test_case.code
                },
                "assigned_by": assignment.assigned_by.username,
                "status": assignment.status,
                "priority": assignment.priority,
                "deadline": assignment.deadline,
                "notes": assignment.notes,
                "created_at": assignment.created_at
            })

        return Response({"assignments": data})
    
class ManagerAssignmentsView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        """
        Get all assignments for the current user (manager)
        """


        assignments = TestAssignment.objects.filter(
            assigned_by=request.user
        ).exclude(  # Add this exclude clause
                status__in=['completed_pass', 'completed_fail']
        ).select_related('test_case', 'assigned_to')

        data = []
        for assignment in assignments:
            data.append({
                "id": assignment.id,
                "test_case": {
                    "id": assignment.test_case.id,
                    "name": assignment.test_case.name,
                    "code": assignment.test_case.code,
                    "application_id": assignment.test_case.application.id,
                    "application_name": assignment.test_case.application.name
                },
                "assigned_to": assignment.assigned_to.username,
                "status": assignment.status,
                "priority": assignment.priority,
                "deadline": assignment.deadline,
                "notes": assignment.notes,
                "created_at": assignment.created_at
            })

        return Response({"assignments": data})