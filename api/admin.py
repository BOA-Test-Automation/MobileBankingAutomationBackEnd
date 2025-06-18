from django.contrib import admin
from .models import Parser
from .models import TestStepFake
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
admin.site.register(TestStepFake)

@admin.register(Parser)
class ParserAdmin(admin.ModelAdmin):
    print("Hello")
    list_display = ['id', 'created_at', 'show_parsed_steps']
    readonly_fields = ['show_parsed_steps']

    def show_parsed_steps(self, obj):
        steps = obj.parse_steps()
        if not steps:
            return "No steps parsed"

        return steps

    show_parsed_steps.short_description = "Parsed Steps"
    show_parsed_steps.allow_tags = True  


