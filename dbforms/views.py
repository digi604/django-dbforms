from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.shortcuts import render_to_response
from django.template import loader
from django.template.context import Context, RequestContext
from django.template.defaultfilters import slugify, yesno
from django.utils.translation import ugettext as _

from dbforms.models import Form

# Create your views here.
def handle_contactform(request, id, template="contactform/form_submit.html", contact_form=None):
    context = {}
    contact_form = Form.objects.get(pk=id)

    if request.method == 'POST':
        # process the submitted form
        form = contact_form.get_form_class()(request.POST, request.FILES)
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
            for field in contact_form.form.field_set.all():
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
            text_template = loader.get_template('contactform/form_email.txt')
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
            context.update({
                'form': form,
                'success': contact_form.form.success_message.strip() or _("Your request has been submitted. We will process it as soon as possible."),
            })
            return render_to_response(template, context, RequestContext(request))
        else:
            context.update({
                'form': form,
                'contact_form': contact_form,
            })
            return render_to_response(template, context, RequestContext(request))

    # display the form
    else:
        context.update({
            'form': contact_form.get_form_class()(),
            'contact_form': contact_form,
        })
        
    return render_to_response(template, context)
