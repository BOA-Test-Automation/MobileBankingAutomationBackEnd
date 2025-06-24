from functools import wraps
from django.http import JsonResponse

def role_required(allowed_roles):
    def decorator(view_method):
        @wraps(view_method)
        def _wrapped_view(self, request, *args, **kwargs):
            user = getattr(request, 'user', None)
            print(user)
            if user is None or not user.is_authenticated:
                return JsonResponse({"error": "Unauthorizedm2"}, status=401)

            role = getattr(user, 'role', None)
            if role not in allowed_roles:
                return JsonResponse({"error": "Forbidden. Role not allowed."}, status=403)

            return view_method(self, request, *args, **kwargs)
        return _wrapped_view
    return decorator
