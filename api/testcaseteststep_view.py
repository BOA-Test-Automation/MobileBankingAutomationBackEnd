from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin
from rest_framework import status
from .models import *
from .serializers import TestCaseSerializer
from django.db import IntegrityError
from django.db.utils import DataError
from rest_framework.exceptions import ValidationError

class CreateTestCaseWithStepsAPIView(APIView):
    def clean_element_id(self, element_id):
        return element_id.replace('\"', '"')

    def post(self, request):
        testcase_data = {
            'code': request.data.get('code', '').strip(),
            'name': request.data.get('name', '').strip(),
            'description': request.data.get('description', '').strip(),
            'application_id': request.data.get('application_id'),
            'suite_id': request.data.get('suite_id'),
            # 'application_id': request.data.get('id'),
            # 'suite_id': request.data.get('module_id')
        }

        recorded_actions = request.data.get('recorded_actions', [])
        
        # Validate required fields
        required_fields = ['name', 'application_id', 'suite_id']
        if not all(testcase_data[field] for field in required_fields):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not recorded_actions:
            return Response({'error': 'No recorded actions provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create test case
            testcase_serializer = TestCaseSerializer(data=testcase_data, context={'request': request})
            testcase_serializer.is_valid(raise_exception=True)
            testcase = testcase_serializer.save(created_by=request.user if request.user.is_authenticated else User.objects.get(id=1))

            # Process recorded actions
            element_map = {}
            saved_steps = []
            step_order = 1
            
            for action in recorded_actions:
                action_type = action['action'].lower()
                params = action['params']
                
                # Process findAndAssign actions
                if action_type == 'findandassign':
                    if len(params) < 3:
                        raise ValidationError("Invalid findAndAssign parameters")
                    
                    by_flag, value, el = params[:3]
                    identifier_type = self._get_identifier_type(by_flag)
                    element_map[el] = {
                        'element_id': self.clean_element_id(value),
                        'element_identifier_type': identifier_type
                    }
                    continue
                
                # Process interaction actions (click, sendKeys)
                if action_type in ['click', 'sendkeys']:
                    if not params or not params[0]:
                        raise ValidationError(f"Missing element reference in {action_type} action")
                    
                    el = params[0]
                    if el not in element_map:
                        raise ValidationError(f"Element {el} referenced before being defined")
                    
                    step_data = {
                        'testcase': testcase,
                        'step_order': step_order,
                        'element_id': element_map[el]['element_id'],
                        'element_identifier_type': element_map[el]['element_identifier_type'],
                        'action': 'click' if action_type == 'click' else 'send_keys'
                    }
                    
                    # Handle sendKeys specific data
                    if action_type == 'sendkeys':
                        step_data.update({
                            'input_field_type': 'dynamic' if action.get('dynamic', False) else 'static',
                            'parameter_name': action.get('label', ''),
                            'input_type': action.get('sendKeysType', 'static'),
                            'actual_input': params[2] if len(params) > 2 else None
                        })
                    
                    # Create the step
                    step = TestStepTest.objects.create(**step_data)
                    saved_steps.append({
                        'id': step.id,
                        'step_order': step.step_order,
                        'action': step.action,
                        'element_id': step.element_id,
                        'element_identifier_type': step.element_identifier_type.name,
                        'input_type': step.input_type,
                        'parameter_name': step.parameter_name,
                        'input_field_type': step.input_field_type,
                        'actual_input': step.actual_input
                    })
                    step_order += 1

            return Response({
                "message": "Test case and steps created successfully",
                "testcase": {
                    "id": testcase.id,
                    "code": testcase.code,
                    "name": testcase.name
                },
                "steps": saved_steps,
                "total_steps": len(saved_steps)
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _get_identifier_type(self, by_flag):
        by_flag = str(by_flag).strip().replace("-", "").lower()
        identifier_map = {
            "android uiautomator": "ANDROID_UIAUTOMATOR",
            "id": "ID",
            "class name": "CLASS_NAME",
            "xpath": "XPATH",
            "accessibility id": "ACCESSIBILITY_ID"
        }
        identifier_type = identifier_map.get(by_flag)
        if not identifier_type:
            raise ValidationError(f"Unsupported locator strategy: {by_flag}")
        
        try:
            return ElementIdentifierType.objects.get(name=identifier_type)
        except ElementIdentifierType.DoesNotExist:
            raise ValidationError(f"Invalid identifier type: {identifier_type}")
