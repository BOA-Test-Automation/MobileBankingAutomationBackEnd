from django.db import models
import re
from django.contrib.auth.models import AbstractUser
from django.utils.html import format_html
import json

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('tester', 'Tester'),
        ('designer', 'Designer'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='api_user_groups',  # Changed
        related_query_name='api_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='api_user_permissions',  # Changed
        related_query_name='api_user',
    )

    def __str__(self):
        return self.username

class Application(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

class TestSuite(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



class TestCase(models.Model):
    code = models.CharField(max_length=255)
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# class TestStepFake(models.Model):
#     record = models.ForeignKey(Parser, related_name='parser', on_delete=models.CASCADE, blank=True, null=True)
#     step_order = models.PositiveIntegerField()
#     identifier_type = models.CharField(max_length=100)
#     element_id = models.TextField()
#     action = models.CharField(max_length=50)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         ordering = ['step_order']

#     def __str__(self):
#         return f"Step {self.step_order} for TestCase {self.testcase.id}"



class ElementIdentifierType(models.Model):
    IDENTIFIER_TYPES = [
        ('ANDROID_UIAUTOMATOR', 'Android UIAutomator'),
        ('CLASS_NAME', 'Class Name'),
        ('ID', 'ID'),
        ('XPATH', 'XPath'),
    ]
    name = models.CharField(max_length=20, choices=IDENTIFIER_TYPES, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestStepTest(models.Model):
    testcase = models.ForeignKey(TestCase, related_name='stepstest', on_delete=models.CASCADE, blank=True, null=True)
    step_order = models.PositiveIntegerField()
    element_identifier_type = models.ForeignKey(
        ElementIdentifierType, 
        on_delete=models.PROTECT,
        related_name='test_steps',
        null=True, blank=True, default=None
    )
    element_id = models.TextField()
    action = models.CharField(max_length=50)
    input_type = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., dynamic or static
    parameter_name = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., "Phone Number"
    input_field_type = models.CharField(max_length=50, null=True, blank=True, default='text') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"Step {self.step_order} for TestCase {self.testcase.id}"


class TestStep(models.Model):
    ACTION_CHOICES = [
        ('click', 'Click'),
        ('swap', 'Swap'),
        ('send_keys', 'Send Keys'),
    ]
    INPUT_TYPE_CHOICES = [
        ('static', 'Static'),
        ('dynamic', 'Dynamic'),
    ]
    INPUT_FIELD_TYPE_CHOICES = [
        ('password', 'Password'),
        ('number', 'Number'),
        ('text', 'Text'),
        ('select', 'Select'),
    ]
    
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    step_order = models.PositiveIntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    element_identifier_type = models.ForeignKey(
        ElementIdentifierType, 
        on_delete=models.PROTECT,
        related_name='test_step',
        null=True, blank=True, default=None
    )
    element_id = models.TextField()
    input_type = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., dynamic or static
    parameter_name = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., "Phone Number"
    input_field_type = models.CharField(max_length=50, null=True, blank=True, default='text') 
    element_screenshot = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']
        unique_together = ('testcase', 'step_order')

class TestAssignment(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_assignments_made' )
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE,  related_name='test_assignments_received')
    execution = models.ForeignKey('TestExecution', on_delete=models.SET_NULL, blank=True, null=True)
    batch = models.ForeignKey('BatchAssignment', on_delete=models.SET_NULL, blank=True, null=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestType(models.Model):
     name = models.CharField(max_length=255)
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)

class BatchAssignment(models.Model):
    name = models.CharField(max_length=255)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_assignments_made')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_assignments_received')
    assignment_type = models.ForeignKey(TestType, on_delete=models.CASCADE)
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    priority = models.CharField(max_length=10, choices=TestAssignment.PRIORITY_CHOICES, default='medium')
    deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BatchAssignmentTestCase(models.Model):
    batch = models.ForeignKey(BatchAssignment, on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CustomTestGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CustomTestGroupTestCase(models.Model):
    group = models.ForeignKey(CustomTestGroup, on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Device(models.Model):
    device_name = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestExecution(models.Model):
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    executed_on = models.ForeignKey(Device, on_delete=models.SET_NULL, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StepResult(models.Model):
    test_execution = models.ForeignKey(TestExecution, on_delete=models.CASCADE)
    test_step = models.ForeignKey(TestStep, on_delete=models.CASCADE)
    actual_xpath = models.TextField(blank=True, null=True)
    actual_screenshot = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)  # in seconds
    log_message = models.TextField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UIComparator(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    figma_design = models.CharField(max_length=255)
    actual_ui = models.CharField(max_length=255)
    difference = models.CharField(max_length=255)
    interactive_html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
