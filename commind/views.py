# -*- coding: utf-8 -*-


from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from .models import Document, Application, Property
from .forms import CommIndApplicationForm, EntityMemberFormSet, EntityForm
#, CommIndDocumentFormset
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings


# This function sends a Document to the user. Used instead of direct download so we can enforce
# permissions. In the future use a library such as fleep or magic to determine the actual
# file type and set content_type appropriately. That would help open PDFs in browser, etc.
def view_document(request, filename):
    f2 = 'documents/'+'/'.join(filename.split('/')[0:])
    d = get_object_or_404(Document, file__exact=f2)
    if d.publish is not True and request.user.is_staff is not True and request.user is not d.user:
        return HttpResponseForbidden("Permission denied.")
    else:
        f = open(d.file.path)
        response = HttpResponse(f, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(d.file.name.split('/')[-1],)
        return response

from django.db import transaction
from .models import Entity, Person
@method_decorator(login_required, name='dispatch')
class CommIndApplicationFormView(FormView):
    form_class = CommIndApplicationForm
    template_name = 'commind_application.html'
    success_url = '/commercial_industrial/success'
    def get_initial(self):
        initial = super(CommIndApplicationFormView, self).get_initial()
        if self.kwargs.get('parcel') is not None:
            initial['Property'] = Property.objects.filter(parcel__contains=self.kwargs['parcel']).first()
        return initial

    def get_context_data(self, **kwargs):
        data = super(CommIndApplicationFormView, self).get_context_data(**kwargs)
        data['COMPANY_SETTINGS'] = settings.COMPANY_SETTINGS
        return data


    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):

        if form.validate_for_submission():
            with transaction.atomic():
                entity = Entity(
                    user=self.request.user,
                    name=form.cleaned_data['entity_name'],
                    created=form.cleaned_data['entity_formed'],
                    date_of_creation=form.cleaned_data['entity_formed_date'],
                    location_of_creation=form.cleaned_data['entity_formed_location'],
                )
                entity.save()
                for cnt in [1,2,3,4]:
                    if form.cleaned_data['principal_{}_name'.format(cnt,)] != '':
                        person = Person(
                            entity = entity,
                            name = form.cleaned_data['principal_{}_name'.format(cnt,)],
                            title = form.cleaned_data['principal_{}_title'.format(cnt,)],
                            email = form.cleaned_data['principal_{}_email'.format(cnt,)],
                            phone = form.cleaned_data['principal_{}_phone'.format(cnt,)],
                            address = form.cleaned_data['principal_{}_address'.format(cnt,)],
                            nature_extent_of_interest = form.cleaned_data['principal_{}_ownership_share'.format(cnt,)],
                        )
                        person.save()
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.entity = entity
            self.object.status = Application.COMPLETE_STATUS
            self.object.save() # to get id so ModelMultipleChoiceField can be saved
            self.object.Properties = form.cleaned_data['Properties']
            self.object.save()
            send_mail(
                'Commercial Application received: {0}'.format(form.cleaned_data['Property'],),
                "Application received in blight fight.",
                'info@renewindianapolis.org',
                [ settings.COMPANY_SETTINGS['COMMERCIAL_CONTACT_EMAIL'], ],
            )

            budget_and_financing_file = Document(
                user = self.request.user,
                file = form.cleaned_data['budget_and_financing_file'],
                file_purpose = 'Budget and Financing',
                content_object = self.object,
            )
            budget_and_financing_file.save()
            development_plan_file = Document(
                user = self.request.user,
                file = form.cleaned_data['development_plan_file'],
                file_purpose = 'Development Plan',
                content_object = self.object,
            )
            development_plan_file.save()
        else:
            return self.form_invalid(form)
    #    return HttpResponseRedirect(self.get_success_url())
        return super(CommIndApplicationFormView, self).form_valid(form)

#class CommIndDocumentFormsetView(FormView):
#    form_class = CommIndDocumentFormset
#    template_name = 'commind_application_documents.html'


# class CommIndApplicationFormView(FormView):
#     form_class = CommIndApplicationForm
#     template_name = 'commind_application.html'
#     success_url = 'commercial_industrial/application/'
#     def get_initial(self):
#         initial = super(CommIndApplicationFormView, self).get_initial()
#         if self.kwargs.get('parcel') is not None:
#             initial['Properties'] = Property.objects.filter(parcel__contains=self.kwargs['parcel'])
#         return initial

class CommIndApplicationSuccessView(TemplateView):
     template_name = "commind_application_sucess.html"

class CommIndApplicationDetailView(DetailView):
    model = Application
    context_object_name = 'application'
    template_name = "commind_application_summary.html"
    def get_context_data(self, **kwargs):
        context = super(CommIndApplicationDetailView, self).get_context_data(**kwargs)
        return context


class PropertyListView(ListView):
    model = Property
    template_name = 'commind_property_list.html'

    def get_context_data(self, **kwargs):
        context = super(PropertyListView, self).get_context_data(**kwargs)
        context['published_property_count'] = Property.objects.filter(published=True).count()
        return context
