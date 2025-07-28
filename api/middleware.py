# api/middleware.py
from django.http import JsonResponse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.deprecation import MiddlewareMixin


class JWTAuthenticationFromCookieMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = request.COOKIES.get('access_token')
        print(access_token)
        if request.path in ['/login/', '/api/token/', '/api/token/refresh/']:
            print("Hello Login")
            return self.get_response(request)
        if access_token:
            try:
                validated_token = JWTAuthentication().get_validated_token(access_token)
                user = JWTAuthentication().get_user(validated_token)
                request.user = user
                print(user)
            except (TokenError, InvalidToken):
                return JsonResponse({'detail': 'Invalid or expired tokenjj'}, status=401)
        return None
