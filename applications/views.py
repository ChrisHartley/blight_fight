from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed, JsonResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core import serializers
from django.core.serializers.json import Serializer
#from django.core.serializers.json import DjangoJSONEncoder
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.utils.encoding import is_protected_type
import os
from django.forms import inlineformset_factory


from .forms import ApplicationForm
#from user_files.forms import UploadedFileForm
from .models import Application, Meeting, MeetingLink
from property_inventory.models import Property
from applicants.models import ApplicantProfile
from user_files.models import UploadedFile
from django.contrib.auth.models import User


# used to send confirmation email
from django.core.mail import send_mail
from django.template.loader import render_to_string

from pprint import pprint
import zipfile
import tempfile
from django.utils.text import slugify

from django.views.generic import DetailView, View

import datetime
from dateutil.rrule import *
from dateutil.relativedelta import *

def determine_next_deadline_date():
    next_deadline = datetime.date(2017, 1, 1)
    next_meeting = datetime.date(2017, 1, 1)
    i = 0
    while (next_deadline <= datetime.date.today()):
        start = datetime.date.today()+relativedelta(days=i)
        next_meeting = rrule(MONTHLY, count=1, byweekday=TH(4), dtstart=start)[0].date()
        next_deadline = next_meeting-relativedelta(weekday=FR(-3))
        i=i+1
    return [next_meeting, next_deadline]


def determine_next_meeting_date():
    next_deadline = datetime.date(2007, 1, 1)
    next_meeting = datetime.date(2017, 1, 1)
    i = 0
    while (next_meeting <= datetime.date.today()):
        start = datetime.date.today()+relativedelta(days=i)
        next_meeting = rrule(MONTHLY, count=1, byweekday=TH(4), dtstart=start)[0].date()
        next_deadline = next_meeting-relativedelta(weekday=FR(-3))
        i=i+1
    return [next_meeting, next_deadline]


@login_required
def process_application(request, action, id=None):
    if action == 'edit':
        app = get_object_or_404(Application, id=id, user=request.user)
        if app.frozen == True:
            return HttpResponse("This application has been submitted and can not be editted. To unfreeze this application email {0} at {1}.".format(settings.COMPANY_SETTINGS['APPLICATION_CONTACT_NAME'], settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']), status=403)
        form = ApplicationForm(instance=app, user=request.user, id=app.pk)
    if action == 'new':
        # see if they already have an application with initial status, if so use that one again, if not create one.
        # Problem - multiple browser windows, or multiple browsers (eg start app on phone, continue on computer, then save phone app before computer app,
        # they share an ID and will overwrite each other. So not doing this for now. We'll see if it is a problem having a blank app saved for each app start
        # try:
        # 	app = Application.objects.get(user.request=user, status=Application.INITIAL_STATUS).first()
        # except model.DoesNotExist:
        # 	app = Application(user=request.user, status=Application.INITIAL_STATUS)
        # 	app.save()
        parcel = request.GET.get('parcel', None)
        if parcel:
            try:
                prop = Property.objects.filter(parcel=parcel).exclude(
                    status__contains='Sale approved by MDC').exclude(
                    is_active__exact=False).exclude(
                    status__contains='Sold').exclude(
                    status__contains='BEP').exclude(
                    status__contains='Sale approved by Board of Directors', renew_owned=True).first()
            except Property.DoesNotExist:
                raise Http404("Property does not exist or is not eligible for application")
            app = Application(user=request.user, status=Application.INITIAL_STATUS, Property=prop)
        else:
            app = Application(user=request.user, status=Application.INITIAL_STATUS)
        app.save()
        form = ApplicationForm(instance=app, user=request.user, id=app.pk)
    if action == 'save':
        if request.method != 'POST':
            return HttpResponseNotAllowed('Error - POST required to save')
        app = get_object_or_404(Application, id=id, user=request.user)
        if app.frozen == True:
            return HttpResponse("This application has been submitted and can not be editted. To unfreeze this application email {0} at {1}.".format(settings.COMPANY_SETTINGS['APPLICATION_CONTACT_NAME'], settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']), status=403)
        form = ApplicationForm(request.POST, request.FILES,
                               user=request.user, instance=app, id=app.pk)
        if form.is_valid():
            application = form.save(commit=False)
            if application.status == Application.INITIAL_STATUS:
                application.status = Application.ACTIVE_STATUS
            save_for_later = request.POST.get('save_for_later')
            if not save_for_later:  # they want to submit the application
                if form.validate_for_submission(id=application.id):
                    #application.frozen = True
                    application.status = Application.COMPLETE_STATUS
                    application.save()
                    applicant_email = request.user.email
                    property_address = app.Property
                    msg_plain = render_to_string('email/application_submitted.txt', {
                        'user': request.user,
                        'Property': property_address,
                        'application': application,
                        'COMPANY_SETTINGS': settings.COMPANY_SETTINGS,
                    }
                    )
                    send_mail(
                        'Application received: {0}'.format(property_address),
                        msg_plain,
                        'info@renewindianapolis.org',
                        [applicant_email],
                    )
                    return HttpResponseRedirect(reverse('application_confirmation', args=(id,)))
                else:
                    "*!*!* validate_for_submission() returned false"

            application.frozen = False
            application.save()

    uploaded_files_sow = UploadedFile.objects.filter(
        user=request.user, application=app.id, file_purpose=UploadedFile.PURPOSE_SOW)
    uploaded_files_pof = UploadedFile.objects.filter(
        user=request.user, application=app.id, file_purpose=UploadedFile.PURPOSE_POF)
    uploaded_files_all = UploadedFile.objects.filter(
        user=request.user, application=app.id)

    return render(request, 'application.html', {
        'form': form,
        'app_id': app.id,
        'uploaded_files_sow': uploaded_files_sow,
        'uploaded_files_pof': uploaded_files_pof,
        'uploaded_files_all': uploaded_files_all,
        'title': 'application',
        'COMPANY_SETTINGS': settings.COMPANY_SETTINGS,
        'next_deadline': determine_next_deadline_date()[1],
        'next_meeting': determine_next_deadline_date()[0],
    })


# no longer needed since switching to admin app instead of home rolled dataTables
class DisplayNameJsonSerializer(Serializer):

    def handle_field(self, obj, field):
        value = field._get_val_from_obj(obj)
        display_method = "get_%s_display" % field.name
        if hasattr(obj, display_method):
            self._current[field.name] = getattr(obj, display_method)()
        elif is_protected_type(value):
            self._current[field.name] = value
        else:
            self._current[field.name] = field.value_to_string(obj)

@login_required
def application_confirmation(request, id):
    app = get_object_or_404(Application, id=id, user=request.user)
    return render(request, 'confirmation.html', {
        'title': 'thank you',
        'Property': app.Property,
        'COMPANY_SETTINGS': settings.COMPANY_SETTINGS,
    })

class ApplicationDetail(DetailView):
    model = Application
    context_object_name = 'application'
    template_name = 'application_display.html'

class ApplicationDisplay(DetailView):
    model = Application
    context_object_name = 'application'
    template_name = 'application_detail.html'

class ApplicationNeighborhoodNotification(DetailView):
    model = Application
    context_object_name = 'application'
    template_name = 'neighborhood_notification.html'

class ApplicationPurchaseAgreement(DetailView):
    model = Application
    context_object_name = 'application'
    template_name = 'purchase_agreement.html'

class ReviewCommitteeAgenda(DetailView):
    model = Meeting
    context_object_name = 'meeting'
    template_name = 'rc_agenda.html'

class ReviewCommitteeStaffSummary(DetailView):
    model = Meeting
    context_object_name = 'meeting'
    template_name = 'application_display_all.html'

class ReviewCommitteeApplications(DetailView):
    model = Meeting
    context_object_name = 'meeting'
    template_name = 'application_detail_all.html'


class CreateMeetingSupportArchive(View):
    def get(self, request, *args, **kwargs):
        meeting_id = self.kwargs['pk']
        meeting = get_object_or_404(Meeting, id=meeting_id)
        with tempfile.SpooledTemporaryFile() as tmp:
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as myzip:
                for meeting_link in meeting.meeting_link.all():
                    application = meeting_link.application
                    uploaded_files = UploadedFile.objects.filter(application=application).exclude(file_purpose=UploadedFile.PURPOSE_POF)
                    for uploaded_file in uploaded_files:
                        filename = str(uploaded_file.supporting_document.name)
                        if filename.startswith('/') != True:
                            filename = settings.MEDIA_ROOT+filename
                        archive_filename = '{0}_{1}/{2}'.format(slugify(application.Property), slugify(application.user.first_name+' '+application.user.last_name), os.path.basename(filename))
                        myzip.write(filename, archive_filename)
            tmp.seek(0)
            response = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
            response['Content-Disposition'] = 'attachment; filename="{0}.zip"'.format(meeting,)
            return response


import csv
class PriceChangeCSVResponseMixin(object):
    """
    A mixin that constructs a CSV response from the context data if
    the CSV export option was provided in the request.
    """
    def render_to_response(self, context, **response_kwargs):
        """
        Creates a CSV response if requested, otherwise returns the default
        template response.
        """
        # Sniff if we need to return a CSV export
        if 'csv' in self.request.GET.get('export', ''):
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{0}-{1}"'.format(slugify(context['meeting']), 'price-changes.csv')
            writer = csv.writer(response)

            header = ['Property', 'Structure Type', 'Current Price', 'Proposed Price', 'Price Difference']
            writer.writerow(header)
            price_change_total = 0
            # Write the data from the context somehow
            for price_change_link in context['meeting'].price_change_meeting_link.all():
                price_change = price_change_link.price_change.proposed_price - price_change_link.price_change.Property.price
                price_change_total = price_change_total + price_change
                row = [price_change_link.price_change.Property, price_change_link.price_change.Property.structureType, price_change_link.price_change.Property.price, price_change_link.price_change.proposed_price, price_change]
                writer.writerow(row)
            writer.writerow(['Total Change', price_change_total])
            return response
        # Business as usual otherwise
        else:
            return super(PriceChangeCSVResponseMixin, self).render_to_response(context, **response_kwargs)

class PriceChangeSummaryAll(PriceChangeCSVResponseMixin, DetailView):
    model = Meeting
    context_object_name = 'meeting'
    template_name = 'price_change_summary_view_all.html'

class CreateMeetingPriceChangeCMAArchive(View):
    def get(self, request, *args, **kwargs):
        meeting_id = self.kwargs['pk']
        meeting = get_object_or_404(Meeting, id=meeting_id)
        with tempfile.SpooledTemporaryFile() as tmp:
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as myzip:
                for price_change_link in meeting.price_change_meeting_link.all():
                    filename = str(price_change_link.price_change.cma.name)
                    #print price_change_link.price_change.cma
                    if price_change_link.price_change.cma.name == 'None':
                        pass
                    if filename.startswith('/') != True:
                        filename = settings.MEDIA_ROOT+filename
                    #print price_change_link.price_change
                    #print filename
                    archive_filename = '{0}.pdf'.format(slugify(price_change_link.price_change),)
                    try:
                        myzip.write(filename, archive_filename)
                    # if the file can't be opened or doesn't exist, eg in testing environment, then skip it.
                    except OSError:
                        pass
            tmp.seek(0)
            response = HttpResponse(tmp.read(), content_type='application/x-zip-compressed')
            response['Content-Disposition'] = 'attachment; filename="{0}-CMAs.zip"'.format(meeting,)
            return response


import csv
from decimal import *
class MDCCSVResponseMixin(object):
    """
    A mixin that constructs a CSV response from the context data if
    the CSV export option was provided in the request.
    """
    def render_to_response(self, context, **response_kwargs):
        """
        Creates a CSV response if requested, otherwise returns the default
        template response.
        """
        # Sniff if we need to return a CSV export
        if 'csv' in self.request.GET.get('export', ''):
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{0}-{1}"'.format(slugify(context['meeting']), 'MDC-for-resolution.csv')
            writer = csv.writer(response)

            header = ['Parcel','Street Address','Application Type','Structure Type','City\'s Sale Price','Renew\'s Sale Price','Total','Buyer Name']
            writer.writerow(header)
            # Write the data from the context somehow
            #from applications.models import MeetingLink.APPROVED_STATUS
            for meeting_link in context['meeting'].meeting_link.all().order_by('application__application_type').filter(application__Property__renew_owned__exact=False).filter(meeting_outcome=MeetingLink.SCHEDULED_STATUS):
                application = meeting_link.application
                if application.application_type == application.SIDELOT:
                    price = 750 # hardcoded value for sidelots. Big trouble!
                    city_split = 250
                    renew_split = 500
                elif application.Property.price > 3500:
                    price = application.Property.price
                    city_split = round(price*Decimal('.55'))
                    renew_split = Decimal(price)-Decimal(city_split)
                elif application.Property.price == 3500.0:
                    price = application.Property.price
                    city_split = 1000.00
                    renew_split = 2500.00
                elif application.Property.price == 750.0:
                    price = application.Property.price
                    city_split = 250.00
                    renew_split = 500.00
                else:
                    city_split = 0
                    renew_split = 0
                total = Decimal(city_split)+Decimal(renew_split)
                if application.organization:
                    buyer = '{0} {1}, {2}'.format(application.user.first_name, application.user.last_name, application.organization.name)
                else:
                    buyer = '{0} {1}'.format(application.user.first_name, application.user.last_name)
                row = [application.Property.parcel, application.Property.streetAddress, application.get_application_type_display(), application.Property.structureType, city_split, renew_split, total, buyer]
                writer.writerow(row)
            return response
        # Business as usual otherwise
        else:
            return super(MDCCSVResponseMixin, self).render_to_response(context, **response_kwargs)


class MDCSpreadsheet(MDCCSVResponseMixin, DetailView):
    model = Meeting
    context_object_name = 'meeting'
    template_name = 'price_change_summary_view_all.html'
