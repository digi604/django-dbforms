# Generate CSV files for models
from django.utils.encoding import smart_str, smart_unicode
from django.db.models.fields.related import ManyToManyField
import re
from django.db.models.loading import get_model, get_apps, get_models
from django.db.models import BooleanField
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template.defaultfilters import yesno

from csv_export.views import _field_extractor_function, UnicodeWriter, DatabaseInconsistency

from pprint import pprint

@staff_member_required
def export(request, app_label='contactform', model_name='contactformsubmission'):
    """Return a CSV file for this table."""

    # Get the fields of the table
    model = get_model(app_label, model_name)
    if not model:
        raise Http404
    fields1 = model._meta.fields
    fields = []
    for f in fields1:
        if not f.name in ['form_data', 'form_data_pickle']:
            fields.append(f)
    field_funcs = [ _field_extractor_function(f) for f in fields ]

    # set the HttpResponse
    response = HttpResponse(mimetype='text/csv;charset=ISO-8859-1')
    response['Content-Disposition'] = 'attachment; filename=%s-%s.csv' % (app_label, model_name)
    writer = UnicodeWriter(response, encoding='iso8859-1', illegal_char_replacement='?')
    
    
    # Do some simple query string check for filters
    filters = {}
    for param_name, param_value in request.REQUEST.items():
        if re.match(r'.+__(exact|lte|gte|year|month)', param_name):
            filters[str(param_name)] = param_value
    # Write all rows of the CSV file
    model_objects = model.objects.all().filter(**filters)
    #pprint.pprint(model_objects)
    # collect all the extra fields
    extra_fieldnames = []
    for o in model_objects:
        extra_fields = o.form_data_pickle or {}
        for key, value in extra_fields.items():
            #print key, value
            if not key in extra_fieldnames:
                extra_fieldnames.append(key)
    # Write the header of the CSV file
    writer.writerow([ f.verbose_name for f in fields ] + extra_fieldnames )
    
    for o in model_objects:
        try:
            row = [ func(o) for func in field_funcs ]
            extra_fields = o.form_data_pickle or {}
            for fn in extra_fieldnames:
                if fn in extra_fields.keys():
                    row += [ extra_fields[fn] ]
                else:
                    row += [ '' ]
            writer.writerow(row)
        except Exception, e:
            raise DatabaseInconsistency,"there was an error at object %s (%s)" % ( o.id, e )
    # All done
    return response
