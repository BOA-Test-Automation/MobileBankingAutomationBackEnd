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

# class CreateTestCaseWithStepsAPIView(APIView):
#     # permission_classes = [IsAuthenticated, IsAdmin]

#     def clean_element_id(self, element_id):
#         return element_id.replace('\"', '"')

#     def post(self, request):
#         testcase_data = {
#             'code': request.data.get('code'),
#             'name': request.data.get('name'),
#             'description': request.data.get('description'),
#             'application_id': request.data.get('application_id'),
#             'suite_id': request.data.get('suite_id'),
#             'input_field_type' : request.data.get('input_field_type'),
#             'label_name' : request.data.get('label_name'),
#             'input_type' : request.data.get('input_type')
#         }

#         recorded_actions = request.data.get('recorded_actions')
#         if not recorded_actions and not request.data.get('code') and not request.data.get('name') and not request.data.get('description') and not request.data.get('application_id') and not request.data.get('suite_id'):
#             print(request.data.get('code'))
#             print(request.data.get('name'))
#             print(request.data.get('description'))

#             return Response({'error': 'Missing Required Fields'}, status=status.HTTP_400_BAD_REQUEST)
        

#         try:
#             user = request.user if request.user.is_authenticated else User.objects.get(id=1)
#             testcase_serializer = TestCaseSerializer(data=testcase_data, context={'request': request})
#             testcase_serializer.is_valid(raise_exception=True)
#             # testcase = testcase_serializer.save(created_by=request.user)
#             testcase = testcase_serializer.save(created_by=user)

#         except IntegrityError as e:
#             if 'Duplicate entry' in str(e):
#                 return Response({'error': 'TestCase with this code, name, suite, and application already exists.'}, status=409)
#             elif 'a foreign key constraint fails' in str(e):
#                 return Response({'error': 'Invalid suite_id or application_id. Foreign key does not exist.'}, status=400)
#             else:
#                 return Response({'error': 'Database error: ' + str(e)}, status=500)
#         except ValidationError as ve:
#             return Response({'error': ve.detail}, status=400)

        

#         # Parse recorded steps
#         parsed_steps = []
#         element_map = {}

#         for action in recorded_actions:
#             action_raw = action.get("action", "").lower()
#             action_map = {
#                 "findandassign": "findAndAssign",
#                 "click": "click",
#                 "sendkeys": "send_keys",
#                 "send_keys": "send_keys",
#             }
#             params = action.get("params", [])
#             normalized_action = action_map.get(action_raw)

#             if normalized_action == "findAndAssign":
#                 by_flag, value, el = params[:3]
#                 by_flag = by_flag.strip().replace("-", "").lower()
#                 identifier_map = {
#                     "android uiautomator": "ANDROID_UIAUTOMATOR",
#                     "id": "ID",
#                     "class name": "CLASS_NAME",
#                     "xpath": "XPATH",
#                     "accessibility id": "ACCESSIBILITY_ID"
#                 }
#                 identifier_type = identifier_map.get(by_flag)
#                 if not identifier_type:
#                     return Response({"error": f"Unsupported by: {by_flag}"}, status=400)
#                 try:
#                     identifier_obj = ElementIdentifierType.objects.get(name=identifier_type)
#                 except ElementIdentifierType.DoesNotExist:
#                     return Response({"error": f"Unsupported identifier: {identifier_type}"}, status=400)

#                 element_map[el] = {
#                     "element_id": value,
#                     "element_identifier_type": identifier_obj
#                 }

#             elif normalized_action in ("click", "send_keys"):
#                 el = params[0]
#                 if el in element_map:
#                     step_data = {
#                         "element_id": element_map[el]["element_id"],
#                         "element_identifier_type": element_map[el]["element_identifier_type"],
#                         "action": normalized_action
#                     }

#                     if normalized_action == "send_keys":
#                         step_data["input_type"] = "dynamic"
#                         step_data["parameter_name"] = "Phone Number"
#                         step_data["input_field_type"] = "text"

#                     parsed_steps.append(step_data)

#         for i, step in enumerate(parsed_steps, 1):
#             TestStepTest.objects.create(
#                 testcase=testcase,
#                 step_order=i,
#                 element_identifier_type=step["element_identifier_type"],
#                 element_id=step["element_id"],
#                 action=step["action"],
#                 input_type=step.get("input_type"),
#                 parameter_name=step.get("parameter_name"),
#                 input_field_type=step.get("input_field_type"),
#             )

#         return Response({"message": f"TestCase and {(recorded_actions)} created successfully.", "testcase_id": testcase.id}, status=200)


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
                            'input_type': action.get('sendKeysType', 'text'),
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
