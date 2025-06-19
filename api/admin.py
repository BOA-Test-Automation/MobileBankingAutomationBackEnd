from django.contrib import admin
# from .models import TestStepFake
from .models import * 

admin.site.register(User)
admin.site.register(Application)
admin.site.register(TestSuite)
admin.site.register(TestCase)
admin.site.register(ElementIdentifierType)
admin.site.register(TestStep)
admin.site.register(TestAssignment)
admin.site.register(TestType)
admin.site.register(BatchAssignment)
admin.site.register(CustomTestGroup)
admin.site.register(BatchAssignmentTestCase)
admin.site.register(CustomTestGroupTestCase)
admin.site.register(Device)
admin.site.register(TestExecution)
admin.site.register(StepResult)
admin.site.register(UIComparator)
admin.site.register(TestStepTest)




