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

    class Meta:
        db_table = 'api_user'  

    def __str__(self):
        return self.username

class Application(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

class TestSuite(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('application', 'name')
        verbose_name = 'Test Suite'
        verbose_name_plural = 'Test Suites'

    def __str__(self):
        return f"{self.name} - {self.application.name}"



class TestCase(models.Model):
    code = models.CharField(max_length=255, blank=True, null=True)
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def get_default_user():
       return User.objects.filter(username='admin').first().id
    
    # or default=get_default_user
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('name', 'suite', 'application')

class ElementIdentifierType(models.Model):
    IDENTIFIER_TYPES = [
        ('ANDROID_UIAUTOMATOR', 'Android UIAutomator'),
        ('CLASS_NAME', 'Class Name'),
        ('ID', 'ID'),
        ('XPATH', 'XPath'),
        ("ACCESSIBILITY_ID", "ACCESSIBILITY ID")
    ]
    name = models.CharField(max_length=20, choices=IDENTIFIER_TYPES, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestStepTest(models.Model):

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

    testcase = models.ForeignKey(TestCase, related_name='stepstest', on_delete=models.CASCADE, blank=True, null=True)
    step_order = models.PositiveIntegerField()
    element_identifier_type = models.ForeignKey(
        ElementIdentifierType, 
        on_delete=models.PROTECT,
        related_name='test_steps',
        null=True, blank=True, default=None
    )
    element_id = models.TextField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    actual_input = models.CharField(max_length=250, null=True, blank=True, default=None)
    input_type = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., dynamic or static
    parameter_name = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., "Phone Number"
    input_field_type = models.CharField(max_length=50, null=True, blank=True, default='static')
    element_screenshots = models.CharField(max_length=255, blank=True, null=True)
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
    actual_input = models.CharField(max_length=250, null=True, blank=True, default=None)
    input_type = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., dynamic or static
    parameter_name = models.CharField(max_length=100, null=True, blank=True, default=None)  # e.g., "Phone Number"
    input_field_type = models.CharField(max_length=50, null=True, blank=True, default='text') 
    element_screenshot = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']
        unique_together = ('testcase', 'step_order')

class Device(models.Model):
    device_uuid = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=255)
    platform = models.CharField(max_length=255)
    os_version = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestExecution(models.Model):
    STATUS_CHOICES = [
        ('passed', 'Completed_Passed'),
        ('failed', 'Completed_Failed'),
        ('in_progress', 'In_Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    batch = models.ForeignKey('BatchAssignment', on_delete=models.CASCADE, related_name='assigned_objects', blank=True, null=True)
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    executed_device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device', blank=True, null=True)
    overallstatus = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestAssignment(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_assignments_made' )
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE,  related_name='test_assignments_received')
    execution = models.ForeignKey(TestExecution, on_delete=models.SET_NULL, blank=True, null=True)
    batch = models.ForeignKey('BatchAssignment', on_delete=models.SET_NULL, blank=True, null=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed_pass', 'Completed_Pass'),
        ('completed_fail', 'Completed_Fail')
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

# class CustomTestGroup(models.Model):
#     name = models.CharField(max_length=255, default=None)
#     application = models.ForeignKey(Application, on_delete=models.CASCADE,  related_name='application_id', default=None)
#     description = models.CharField(max_length=255)
#     created_by = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)


class CustomTestGroup(models.Model):
    name = models.CharField(max_length=255, default=None)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='application_id', default=None)
    description = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add this property to get test cases
    @property
    def test_cases(self):
        return TestCase.objects.filter(
            id__in=CustomTestGroupItems.objects.filter(
                custom_group=self
            ).values_list('test_case_id', flat=True)
        )

class CustomTestGroupItems(models.Model):
    custom_group = models.ForeignKey(CustomTestGroup, on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    order_ingroup =models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BatchAssignment(models.Model):
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    name = models.CharField(max_length=255)
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_assignments_made')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_assignments_received')
    assignment_type = models.ForeignKey(TestType, on_delete=models.CASCADE, default='1')
    customgroup = models.ForeignKey(CustomTestGroup, on_delete=models.SET_NULL, null=True, blank=True)
    application = models.ForeignKey('Application', on_delete=models.SET_NULL, null=True, blank=True)
    suite = models.ForeignKey('TestSuite', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=10, choices=TestAssignment.PRIORITY_CHOICES, default='medium')
    totaltestcases = models.IntegerField(blank=True, null=True)
    completedtestcases = models.IntegerField(blank=True, null=True)
    passedtestcases = models.IntegerField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def test_cases(self):
        if self.customgroup:
            return self.customgroup.test_cases  # Uses the property we just added
        elif self.application:
            return TestCase.objects.filter(application=self.application)
        elif self.suite:
            return TestCase.objects.filter(suite=self.suite)
        return TestCase.objects.none()
    
    class Meta:
        unique_together = ('name', "assigned_by", "application", "customgroup", "suite")


class BatchAssignmentTestCase(models.Model):
    batch = models.ForeignKey(BatchAssignment, on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    execution = models.ForeignKey(TestExecution, on_delete=models.CASCADE, related_name='execution', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StepResult(models.Model):
    test_execution = models.ForeignKey(TestExecution, on_delete=models.CASCADE)
    # test_step = models.ForeignKey(TestStep, on_delete=models.CASCADE)
    test_step = models.ForeignKey(TestStepTest, on_delete=models.CASCADE)
    actual_id = models.TextField(blank=True, null=True)
    actual_input = models.CharField(max_length=20, blank=True, null=True)
    actual_screenshot = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)  # in seconds
    time_start = models.DateTimeField(blank=True, null=True)
    time_end = models.DateTimeField(blank=True, null=True)
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
