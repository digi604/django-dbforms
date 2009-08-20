from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from cms.plugin_pool import plugin_pool
from cms.plugin_base import CMSPluginBase
from dbforms.models import ContactFormIntermediate, FormSubmission
from django.template.context import Context
from django.template.defaultfilters import slugify, yesno
from django.contrib.sites.models import Site
from django.template import loader
from django.core.mail import EmailMessage
from django.conf import settings
from pprint import pprint

class ContactFormPlugin(CMSPluginBase):
    model = ContactFormIntermediate
    name = _("Contact Form")
    placeholders = ("content",)
    render_template = "dbform/form.html"
    form_template = "dbform/plugin_form.html"
    
    def render(self, context, instance, placeholder):
        request = context['request']
        contact_form = instance.form
        FormClass = contact_form.get_form_class()
        my_context = Context({
            'placeholder': placeholder,
            'contact_form': contact_form, 
            'form_instance': FormClass(),
            'current_page': request.current_page,
            'page': request.current_page,
        })
        if request.method == 'POST' and "contactform_id" in request.POST \
            and request.POST['contactform_id'] == str(contact_form.id):
            # process the submitted form
            form = FormClass(request.POST, request.FILES)
            if form.is_valid():
                site = Site.objects.get_current()
                try:
                    from siteinfo.models import SiteSettings
                    contact = SiteSettings.objects.get_current()
                except:
                    contact = None
                subject = u"[%s] %s" % (site.domain, _(u"Contact form sent"))
                print site.domain
                # render fields
                rows = ''
                files = []
                to_pickle = {}
                for field in contact_form.field_set.all():
                    field_label = slugify(field.get_label())
                    value = form.cleaned_data[field_label]
                    if isinstance(value, bool):
                        value = yesno(value, u"%s,%s" % (_('yes'), _('no')),)
                    if field.field_type == 'FileField':
                        if field_label in request.FILES:
                            this_file = request.FILES[field_label]
                            if this_file.size > 10240: # check if file is bigger than 10 MB (which is not good)
                                files.append(this_file)
                    rows += u"%s: %s\n" % (form.fields[field_label].label, value)
                    to_pickle[unicode(field_label)] = unicode(value)
                    # use the verbose fieldname instead
                    #to_pickle[form.fields[field_label].label] = value
                #pprint(to_pickle)
                
                message_context = Context({
                    'site': site,
                    'form': form,
                    'contact_form': contact_form,
                    'rows': rows,
                    'sender_ip': request.META['REMOTE_ADDR'],
                    'form_url': request.build_absolute_uri(),
                }, autoescape=False)
                text_template = loader.get_template('dbform/form_email.txt')
                text_content = text_template.render(message_context)
                recipient_list = [recipient['email'] for recipient in contact_form.recipients.values('email')]
                bcc = []
                if contact_form.cc_managers:
                    bcc += [manager[1] for manager in settings.MANAGERS]
                if contact_form.cc_site_contact and contact:
                    bcc += [contact.email]
                message = EmailMessage(subject=subject, body=text_content, from_email=settings.DEFAULT_FROM_EMAIL, to=recipient_list, bcc=bcc)
                for file in files:
                    message.attach(file.name, file.read(2621440), file.content_type)
                message.send()
                my_context.update({
                    'form_instance': form,
                    'success': mark_safe(contact_form.success_message.strip() or _("Your request has been submitted. We will process it as soon as possible.")),
                })
                # save message to db for later reference
                submission = FormSubmission(
                                form=contact_form,
                                sender_ip=request.META['REMOTE_ADDR'],
                                form_url=request.build_absolute_uri(),
                                language=contact_form.language,
                                form_data=text_content,
                                form_data_pickle=to_pickle)
                submission.save()
            else:
                my_context.update({
                    'form_instance': form,
                    'contact_form': contact_form,
                })
        return my_context
    
plugin_pool.register_plugin(ContactFormPlugin)
