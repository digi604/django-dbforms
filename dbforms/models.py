from django.db import models
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_str
from django.template.defaultfilters import slugify
from django.conf import settings
from django.utils.safestring import mark_safe

from fields import PickledObjectField

if 'siteinfo' in settings.INSTALLED_APPS:
    try:
        from siteinfo.models import SiteSettings
        site_contact_email = SiteSettings.objects.get_current().email
    except ImportError, Exception:
        site_contact_email = 'n/a'
else:
    site_contact_email = 'n/a'
    

class Form(models.Model):
    language = models.CharField(_('language'), max_length=2, choices=settings.LANGUAGES)
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    success_message = models.TextField(_('success message'), blank=True)
    recipients = models.ManyToManyField('Recipient', verbose_name=_('recipients'))
    cc_managers = models.BooleanField(_('CC to managers'), help_text=_('Check to send a copy to the site managers (%s).' % (u','.join([manager[1] for manager in settings.MANAGERS]))))
    cc_site_contact = models.BooleanField(_('CC to site contact'), help_text=_('Check to send a copy to the site contact (%s).' % (site_contact_email)))
    
    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.language)

    def get_form_class(self):
        class DynamicForm(forms.Form):
            def __init__(self, *args, **kwargs):
                forms.Form.__init__(self, *args, **kwargs)
            def save(self):
                "Do the save"
        for field in self.field_set.all():
            if field.widget == '':
                widget = None
            else:
                widget = getattr(forms.widgets, field.widget)
            
            label=field.label
            if field.field_type == 'BooleanField':
                label=mark_safe(label)
            form_field = getattr(forms.fields, field.field_type)(required=field.required, widget=widget, label=label)#, initial=field.initial, help_text=field.help_text)
            setattr(DynamicForm, slugify(field.label), form_field)
        form_class = type(smart_str(slugify(self.name) + 'Form'), (DynamicForm,), dict(DynamicForm.__dict__))
        return form_class
    
    class Meta:
        verbose_name = _('contact form')
        verbose_name_plural = _('contact forms')
    
class FormField(models.Model):
    FIELD_TYPES = (
        ('CharField', _('character field')),
        ('EmailField', _('email field')),
        #('DateField', _('date field')),
        ('BooleanField', _('checkbox')),
        ('FileField', _('file field')),
    )
    
    WIDGET_TYPES = (
        ('Textarea', _('textarea')),
        ('PasswordInput', _('password input')),
#        ('RadioSelect', _('radio button')),
#        ('CheckboxInput', _('checkbox')),
    )

    form = models.ForeignKey(Form, related_name='field_set')
    label = models.CharField(max_length=255)
    field_type = models.CharField(choices=FIELD_TYPES, max_length=50)
    widget = models.CharField(choices=WIDGET_TYPES, max_length=50, blank=True)
    required = models.BooleanField()
    position = models.IntegerField(default=1)
    
    def __unicode__(self):
        return u'%s, %s field %s' % (self.label, self.field_type, self.widget)
    
    class Meta:
        ordering = ('position',)
        unique_together = (("form", "label"),)
        
    def get_label(self):
        return self.label

class Recipient(models.Model):
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    
    def __unicode__(self):
        return u'%s, %s' % (self.name, self.email)
    
    class Meta:
        verbose_name = _('recipient')
        verbose_name_plural = _('recipients')

class FormSubmission(models.Model):
    form = models.ForeignKey(Form)
    submitted_at = models.DateTimeField(auto_now_add=True)
    sender_ip = models.IPAddressField()
    form_url = models.URLField(verify_exists=False)
    language = models.CharField(default='unknown', max_length=255)
    form_data = models.TextField(null=True, blank=True)
    form_data_pickle = PickledObjectField(null=True, blank=True, editable=False)
    
    def __unicode__(self):
        return u'%s' % (self.form)
    
    class Meta:
        ordering = ("-submitted_at",)

try:
    from cms.models import CMSPlugin
except ImportError:
    CMSPlugin = None
if not CMSPlugin:
    # django-cms v1 is used
    class ContactFormIntermediate(CMSPlugin):
        form = models.ForeignKey(Form)
        
        def __unicode__(self):
            return u'%s (%s)' % (self.form.name, self.form.language)
else:
    # django-cms v2 is used
    class ContactFormIntermediate(CMSPlugin):
        form = models.ForeignKey(Form)
        
        def __unicode__(self):
            return u'%s (%s)' % (self.form.name, self.form.language)
            
    if 'reversion' in settings.INSTALLED_APPS:
        import reversion
        reversion.register(ContactFormIntermediate, follow=["cmsplugin_ptr"])
