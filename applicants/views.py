from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.forms.formsets import formset_factory
from django.contrib.auth.decorators import login_required
from django.utils.html import escape, escapejs
from django.views.generic import View
from django.urls import reverse


from .forms import ApplicantProfileForm, OrganizationForm
from .models import ApplicantProfile, Organization
from user_files.models import UploadedFile
from .tables import PropertyInquiryTable, ApplicationTable, OrganizationTable, PropertiesUnderPATable
from applications.models import Application
from property_inquiry.models import propertyInquiry
from property_inventory.models import Property
#class CustomFormSignupView(allauth.account.views.SignupView):
#    form_class = CustomSignupForm

@login_required
def profile_home(request):
    try:
        property_inquiries = propertyInquiry.objects.filter(
            user=request.user).order_by('-timestamp')
        property_inquiries_table = PropertyInquiryTable(property_inquiries)
    except propertyInquiry.DoesNotExist:
        property_inquiries_table = None

    try:
        applications = Application.objects.filter(
            user=request.user).exclude(status=Application.INITIAL_STATUS).order_by('-modified')
        applications_table = ApplicationTable(applications)
    except Application.DoesNotExist:
        applications_table = None

    try:
        profile = ApplicantProfile.objects.get(user=request.user)
    except ApplicantProfile.DoesNotExist:
        profile = None

    try:
        organizations = Organization.objects.filter(user=request.user)
        organizations_table = OrganizationTable(organizations)
    except Organization.DoesNotExist:
        organizations_table = None

    try:
        properties_under_pa = Property.objects.filter(buyer_application__user=request.user)
        properties_under_pa_table = PropertiesUnderPATable(properties_under_pa)
    except Property.DoesNotExist:
        properties_under_pa_table = None


    return render(request, 'profile_home.html', {
        'property_inquiries': property_inquiries_table,
        'applications': applications_table,
        'organizations': organizations_table,
        'profile': profile,
        'properties_under_pa': properties_under_pa_table,
        'title': "my account"
    })


@login_required
def showApplicantProfileForm(request):
    success = False
    try:
        profile = ApplicantProfile.objects.get(user=request.user)
    except ApplicantProfile.DoesNotExist:
        profile = None

    if request.method == 'POST':
        ProfileForm = ApplicantProfileForm(
            request.POST, request.FILES, instance=profile)
        if ProfileForm.is_valid():
            pending = ProfileForm.save(commit=False)
            pending.user = request.user
            pending.save()
            success = True
    else:
        ProfileForm = ApplicantProfileForm(instance=profile)
    return render(request, 'create_profile.html', {
        'profileForm': ProfileForm,
        'title': "edit profile",
        'success': success
    })

class edit_organization(View):

    def get(self, request, id=None):
        if '_popup' in request.GET:
            template = 'create_organization_popup.html'
        else:
            template = 'create_organization.html'

        organization = None

        if id:
            organization = get_object_or_404(
                Organization, id=id, user=request.user)
        # else:
        #     organization = Organization(user=request.user)
        form = OrganizationForm(instance=organization)

        uploaded_files = UploadedFile.objects.filter(
            user=request.user, organization=organization)

        return render(request, template, {'title': 'edit organization', 'form': form, 'files': uploaded_files})

    def post(self, request, id=None):
        if '_popup' in request.GET:
            template = 'create_organization_popup.html'
        else:
            template = 'create_organization.html'
        organization = None

        if id:
            organization = get_object_or_404(
                Organization, id=id, user=request.user)
        form = OrganizationForm(
            request.POST, request.FILES, instance=organization)
        if form.is_valid():
            pending = form.save(commit=False)
            pending.user = request.user
            pending.save()
            if '_popup' in request.GET:
                return HttpResponse('<html><body><script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script></body></html>' % (escape(pending.pk), escapejs(pending)))
            return HttpResponseRedirect(reverse('applicants_organization'))
        else:
            return render(request, template, {'title': 'edit organization', 'form': form})


@login_required
def show_organizations(request):
    organizations = Organization.objects.filter(
        user=request.user).order_by('name')
    organizations_table = OrganizationTable(organizations)
    return render(request, 'organizations.html', {
        'organizations': organizations,
        'table': organizations_table,
        'title': "organizations"
    })
