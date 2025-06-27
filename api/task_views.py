from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status  # Renamed import to avoid conflict
from rest_framework.permissions import IsAuthenticated
from .models import TestAssignment, TestCase, User
from .permissions import IsManager
from django.shortcuts import get_object_or_404

class TaskAssignmentView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        """
        Assign a test case to a tester
        Expected POST data:
        {
            "test_case_id": 1,
            "tester_id": 3,
            "manager_id": 2,  # Explicit manager ID
            "notes": "Please test this thoroughly",
            "priority": "high",
            "deadline": "2023-12-31T23:59:59Z"
        }
        """
        test_case_id = request.data.get('test_case_id')
        tester_id = request.data.get('tester_id')
        manager_id = request.data.get('manager_id', request.user.id) # autenticated user with role manger
        notes = request.data.get('notes', '')
        priority = request.data.get('priority', 'medium')
        deadline = request.data.get('deadline')
        assignment_status = 'pending'  

        # Validate required fields
        if not all([test_case_id, tester_id]):
            return Response(
                {"error": "test_case_id and tester_id are required"},
                status=http_status.HTTP_400_BAD_REQUEST  # Using renamed import
            )

        try:
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

            # Create the assignment
            assignment = TestAssignment.objects.create(
                test_case=test_case,
                assigned_by=manager,
                assigned_to=tester,
                notes=notes,
                priority=priority,
                deadline=deadline,
                status=assignment_status  # Using renamed variable
            )

            return Response(
                {
                    "message": "Test case assigned successfully",
                    "assignment_id": assignment.id,
                    "assigned_by": manager.id,
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
    permission_classes = [IsAuthenticated]

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