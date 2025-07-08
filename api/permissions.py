from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        print("Hello")
        return request.user and request.user.role == 'admin'

class IsTester(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == "tester"
    

class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == "manager"
    

class IsDesigner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == "designer"