from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from asgiref.sync import async_to_sync
from .appium_service import AppiumService
import logging
from django.views.decorators.csrf import csrf_exempt
from .appium_service import CriticalStepError

appium_service = AppiumService()

logger = logging.getLogger(__name__)

@csrf_exempt
def get_devices(request):
    if request.method == 'GET':
        devices = async_to_sync(appium_service.get_connected_devices)()
        return JsonResponse(devices)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def start_session(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            driver = async_to_sync(appium_service.start_session)(data)
            return JsonResponse({
                'success': True, 
                'sessionId': driver.session_id
            })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# @csrf_exempt
# def execute_step(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print(f"Received data: {data}")  # Debug input
            
#             # Execute step synchronously with error wrapping
#             try:
#                 result = async_to_sync(appium_service.execute_step)(data)
#                 return JsonResponse(result)
#             except Exception as e:
#                 print(f"Service error: {str(e)}")  # Debug service errors
#                 if isinstance(e, dict) and 'critical' in e:
#                     return JsonResponse({
#                         'success': False,
#                         'error': {str(e)},
#                         'actual_id': e.get('element'),
#                         'duration': 0
#                     }, status=400)
#                 raise
                
#         except Exception as e:
#             print(f"View error: {str(e)}")  # Debug view errors
#             return json({'error' : {str(e)}}, status=500)
        
#     return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def execute_step(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Received data: {data}")  # Debug input
            
            try:
                result = async_to_sync(appium_service.execute_step)(data)
                return JsonResponse(result)
            except Exception as e:
                print(f"Service error: {str(e)}")
                if isinstance(e, dict) and 'critical' in e:
                    return JsonResponse({
                        'success': False,
                        'error': str(e),  # Fixed: using str() instead of set
                        'actual_id': e.get('element'),
                        'duration': 0
                    }, status=400)
                # Return consistent error format for all errors
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'actual_id': None,
                    'duration': 0
                }, status=400)
                
        except Exception as e:
            print(f"View error: {str(e)}")
            return JsonResponse({  # Fixed: using JsonResponse instead of json()
                'success': False,
                'error': str(e),  # Fixed: using str() instead of set
                'actual_id': None,
                'duration': 0
            }, status=500)
        
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def end_session(request):
    if request.method == 'POST':
        try:
            # result = await appium_service.end_session()
            result = async_to_sync(appium_service.end_session)()
            print(result)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)



@csrf_exempt
async def session_info(request):
    if request.method == 'GET':
        try:
            info = await appium_service.get_session_info()
            return JsonResponse(info if info else {'session': None})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)