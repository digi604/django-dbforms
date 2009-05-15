from django import template
from django.template.context import Context
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify, yesno
from django.template import loader
from django.conf import settings
from django.core.mail import EmailMessage

register = template.Library()

class FormNode(template.Node):
    def __init__(self, page):
        self.page = page
        
    def render(self, context):
        page = context[self.page]
        try:
            contact_form = page.contactform_set.get()
            request = context['request']
        except: # ContactForm.DoesNotExist or "django.core.context_processors.request" is not in default context processors 
            return ""
        FormClass = contact_form.get_form_class()
        my_context = Context({
            'contact_form': contact_form, 
            'form_instance': FormClass(),
#            'current_page': page,
#            'page': page,
        }, autoescape=context.autoescape)
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
                subject = _(u"[%s] Contact form sent") % (site.domain)
                # render fields
                rows = ''
                files = []
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
                message_context = Context({
                    'site': site,
                    'form': form,
                    'contact_form': contact_form,
                    'rows': rows,
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
                    'success': contact_form.success_message.strip() or _("Your request has been submitted. We will process it as soon as possible."),
                })
            else:
                my_context.update({
                    'form_instance': form,
                    'dbform': contact_form,
                })
    
        return loader.render_to_string("dbform/form.html", my_context)

@register.tag()
def render_contactform(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, page = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires a single argument" % token.contents.split()[0]
    return FormNode(page)
