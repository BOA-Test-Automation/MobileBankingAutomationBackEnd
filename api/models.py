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

class RecordParserservice(models.Model):
    record = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.record

class Parser(models.Model):

    name = models.CharField(max_length=255, default="New Test Record")
    row_record = models.TextField('Appium Record', help_text="Paste your Appium inspector record here", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Record: {self.name} (ID: {self.id})"


    def parse_steps(self):
        steps = []
        if not self.row_record:
            return steps

        element_lines = self.row_record.splitlines()
        temp_elements = {}

        element_pattern = re.compile(
            r'(?P<el>el\d+)\s*=\s*driver\.find_element\(by=AppiumBy\.(?P<identifier>[A-Z_]+),\s*value="(?P<value>(?:\\.|[^"\\])*)"\)'
        )

        action_pattern = re.compile(
            r'(?P<el>el\d+)\.(?P<action>click|send_keys|swipe)\(?("?[^"]*"?\)?)?'
        )

        for line in element_lines:
            line = line.strip()
            element_match = element_pattern.search(line)
            action_match = action_pattern.search(line)

            if element_match:
                el = element_match.group("el")
                temp_elements[el] = {
                    "element_id": element_match.group("value"),
                    "identifier_type": element_match.group("identifier"),
                }

            if action_match:
                el = action_match.group("el")
                action = action_match.group("action")

                if el in temp_elements:
                    steps.append({
                        "element_id": temp_elements[el]["element_id"],
                        "identifier_type": temp_elements[el]["identifier_type"],
                        "action": action
                    })
                else:
                    print(f"[⚠️ Warning] Action found but element '{el}' was not defined.")

        print(steps)
        return steps

    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        self.steps.all().delete()
        parsed_steps = self.parse_steps()

        for i, step_data in enumerate(parsed_steps, 1):
            TestStepFake.objects.create(
                record=self, 
                step_order=i,
                identifier_type=step_data.get("identifier_type"),
                element_id=step_data.get("element_id"),
                action=step_data.get("action"),
            )


class TestCase(models.Model):
    code = models.CharField(max_length=255)
    suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TestStepFake(models.Model):
    testecase = models.ForeignKey(TestCase, related_name='steps', on_delete=models.CASCADE, blank=True, null=True)
    step_order = models.PositiveIntegerField()
    identifier_type = models.CharField(max_length=100)
    element_id = models.TextField()
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"Step {self.step_order} for TestCase {self.testecase.id}"

class TestStepTest(models.Model):
    testecase = models.ForeignKey(TestCase, related_name='stepstest', on_delete=models.CASCADE, blank=True, null=True)
    step_order = models.PositiveIntegerField()
    identifier_type = models.CharField(max_length=100)
    element_id = models.TextField()
    action = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"Step {self.step_order} for TestCase {self.testecase.id}"


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
    
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    step_order = models.PositiveIntegerField()
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    element_identifier_type = models.ForeignKey(ElementIdentifierType, on_delete=models.PROTECT)
    elementID = models.TextField()
    input_type = models.CharField(max_length=10, choices=INPUT_TYPE_CHOICES, default='static')
    parameter_name = models.CharField(max_length=255, blank=True, null=True)
    input_field_type = models.CharField(max_length=10, choices=INPUT_FIELD_TYPE_CHOICES, default='text')
    element_screenshot = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['step_order']
        unique_together = ('test_case', 'step_order')

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
