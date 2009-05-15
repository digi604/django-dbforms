from django.contrib import admin
from django.contrib.admin.options import TabularInline

from dbforms.models import Form, Recipient, FormField, FormSubmission

class FormFieldInline(TabularInline):
    model = FormField
    num_in_admin = 4 
    extra = 4 
    max_num = 40

class FormAdmin(admin.ModelAdmin):
    inlines = [
        FormFieldInline,
    ]
    list_display = ('name', 'language',)
    list_filter = ('language',)
    search_fields = ('name',)
    ordering = ('id', 'language',)

class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'submitted_at', 'language', 'sender_ip',)
    list_filter = ('form', 'language',)
    search_fields = ('form_data',)

admin.site.register(Form, FormAdmin)
admin.site.register(Recipient)
admin.site.register(FormSubmission, FormSubmissionAdmin)