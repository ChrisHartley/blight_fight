# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline, GenericStackedInline
from django import forms
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.safestring import mark_safe

from .models import Document, Note, Release, InspectionRequest, Inspection
from .models import BreechType, Enforcement, WorkoutMeeting, BreechStatus
from applications.models import Application
from property_inventory.models import take_back
from closings.models import closing

import csv
from django.http import HttpResponse

class NoteInline(GenericStackedInline):
    model = Note
    fields = ('text', 'created', 'modified', )
    readonly_fields=('created', 'modified',)
    extra = 0
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(NoteInline, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'text':
            formfield.widget = forms.Textarea(attrs=formfield.widget.attrs)
        return formfield

class DocumentInline(GenericTabularInline):
    model = Document
    fields = ('file', 'file_purpose',)
    extra = 0

class DocumentAdmin(admin.ModelAdmin):
    search_fields = ('file_purpose',)


class ReleaseInlineAdmin(admin.TabularInline):
    model = Release
    extra = 0
    fields = ('instrument_number', 'recorded_document','date_recorded',)
    #can_delete = False
    show_change_link = True

class InspectionAdmin(admin.ModelAdmin):
    inlines = [NoteInline, DocumentInline, ReleaseInlineAdmin]
    raw_id_fields = ('user',)
    readonly_fields = ('closing_link','application_link')
    search_fields = ('request__Property__streetAddress','request__Property__parcel')


    def closing_link(self, obj):
        tb_link = 'None linked'
        if obj.request.Application is not None:
            try:
                url = reverse("admin:closings_closing_change", args=(closing.objects.filter(application=obj.request.Application).first().id,) )
            except NoReverseMatch:
                pass
            else:
                tb_link = '<a target="_blank" href="{}">{}</a>'.format(
                    url,
                    obj.request.Application.closing_set.first().date_time.strftime('%m/%d/%Y')
                )
        return mark_safe(tb_link)

    def application_link(self, obj):
        tb_link = 'None linked'
        if obj.request.Application is not None:
            url = reverse("admin:applications_application_change", args=(obj.request.Application.id,) )
            tb_link = '<a target="_blank" href="{}">{}</a>'.format(
                url,
                obj.request.Application
            )
        return mark_safe(tb_link)


class InspectionRequestStageFilter(admin.SimpleListFilter):
    title = 'request stage'
    parameter_name = 'stage'

    def lookups(self, request, model_admin):
        return (
            ('new', 'No inspection'),
            ('inspection_passed', 'Inspection passed, no release'),
            ('released', 'Completed and released'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'new':
            return queryset.filter(inspection__isnull=True).distinct()
        if self.value() == 'inspection_passed':
            return queryset.filter(inspection__pass_outcome__exact=True).filter(inspection__release__isnull=True).distinct()
        if self.value() == 'released':
            return queryset.filter(inspection__release__isnull=False).distinct()
        return queryset



class PropertyOwnerFilter(admin.SimpleListFilter):
    title = 'property owner'
    parameter_name = 'owner'
    def lookups(self, request, model_admin):
        return (
            ('true','Renew'),
            ('false', 'DMD'),
            )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(Property__renew_owned__exact=True)
        if self.value() == 'false':
            return queryset.filter(Property__renew_owned__exact=True)

class InspectionRequestAdmin(admin.ModelAdmin):
    inlines = [NoteInline, DocumentInline]
    raw_id_fields = ('user','Application')
    readonly_fields = ('inspection_status','get_contact_info_on_file', 'get_application_and_property_type', 'get_property_owner')
    list_display = ('Property', 'get_application_or_applicant', 'created', 'inspection_status',)
    search_fields = ('Property__parcel', 'Property__streetAddress', 'Application__Property__parcel', 'Application__Property__streetAddress', 'Application__user__last_name', 'Application__user__first_name', 'Application__organization__name')
    list_filter = (InspectionRequestStageFilter,PropertyOwnerFilter)


    ## release exists field
    def inspection_status(self, obj):
        insp = Inspection.objects.filter(request=obj).first()
        result = '-'
        url = ''
        if insp is None:
            result = 'add inspection'
            url = '{}{}{}'.format(reverse("admin:project_agreement_management_inspection_add"), '?request=',obj.id)
        else:
            result = 'add release'
            url = '{}{}{}'.format(reverse("admin:project_agreement_management_release_add"),'?Inspection=',insp.id)
            rel = Release.objects.filter(Inspection=insp).first()
            if rel != None:
#                return mark_safe('done')
                result = 'done'
                url = reverse("admin:project_agreement_management_release_change", args=(rel.id,) )
        il = '<a target="_blank" href="{}">{}</a>'.format(
            url,
            result,
        )
        return mark_safe(il)

    def get_application_and_property_type(self, obj):
        application_type = ''
        property_type = ''
        if obj.Application is not None:
            application_type = obj.Application.get_application_type_display()
        if obj.Property is not None:
            property_type = obj.Property.structureType
        return 'Application Type: {} Property Type: {}'.format(application_type, property_type)

    def get_property_owner(self, obj):
        if obj.Property is not None:
            if obj.Property.renew_owned == True:
                return 'Renew owned'
            else:
                return 'DMD owned'

    def get_application_or_applicant(self, obj):
        if obj.Application is not None:
            url = reverse("admin:applications_application_change", args=(obj.Application.id,) )
            return mark_safe('<a target="_blank" href="{}">{}</a>'.format(url, obj.Application) )
        else:
            return obj.Property.applicant


    def get_contact_info_on_file(self, obj):
        if obj.Application is not None:
            name = '{} {}'.format(obj.Application.user.first_name, obj.Application.user.last_name)
            email = obj.Application.user.email
            phone = obj.Application.user.profile.phone_number
            return '{} {} {}'.format(name, email, phone)
        return 'nothing on file'

class EnforcementInlineAdmin(admin.TabularInline):
    model = Enforcement.meeting.through
    extra = 0
    can_delete = False
    show_change_link = True

class BreechTypesInlineAdmin(admin.TabularInline):
    model = Enforcement.breech_types.through
    extra = 0
    show_change_link = True
    can_delete = False


class BreechStatusAdmin(admin.ModelAdmin):
    raw_id_fields = ('enforcement',)
    inlines = [NoteInline,DocumentInline]
    list_display = ('enforcement','breech', 'status')
    list_filter = ('status', 'breech')
    search_fields = (
        'enforcement__Property__parcel',
        'enforcement__Property__streetAddress',
        'enforcement__Application__user__first_name',
        'enforcement__Application__user__last_name',
        'enforcement__Application__organization__name',
        'enforcement__Application__user__email',
        )
    actions = ['export_as_csv_custom_action',]



    def export_as_csv_custom_action(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format('Breech-enforcement')
        writer = csv.writer(response)

        field_names = [
            'Street Address',
            'Parcel',
            'Structure Type',
            'Application Type',
            'Sale Date',
            'Last Annual Report Submitted',
            'Buyer Name',
            'Organization Name',
            'Buyer email',
            'Buyer phone',
            'Buyer mailing street address',
            'Buyer mailing city',
            'Buyer mailing state',
            'Buyer mailing postal code',
            'Breech Type',
            'Breech opened date',
            'Breech status',
            'Breech closed date',
            'Notes',
            ]

        writer.writerow(field_names)
        for obj in queryset:
            if obj.enforcement.Application is not None:
                from annual_report_form.models import annual_report
                annual_report = annual_report.objects.filter(Property=obj.enforcement.Application.Property).last()
                if annual_report is not None:
                    annual_report_date = annual_report.created
                else:
                    annual_report_date = '-'
                data = [
                    obj.enforcement.Property.streetAddress,
                    obj.enforcement.Property.parcel,
                    obj.enforcement.Property.structureType,
                    obj.enforcement.Application.get_application_type_display(),
                    obj.enforcement.Property.status[5:], # sale date
                    annual_report_date,
                    '{} {}'.format(obj.enforcement.Application.user.first_name, obj.enforcement.Application.user.last_name),
                    obj.enforcement.Application.organization,
                    obj.enforcement.Application.user.email,
                    obj.enforcement.Application.user.profile.phone_number,
                    '{} {} {}'.format(obj.enforcement.Application.user.profile.mailing_address_line1, obj.enforcement.Application.user.profile.mailing_address_line2, obj.enforcement.Application.user.profile.mailing_address_line3),
                    obj.enforcement.Application.user.profile.mailing_address_city,
                    obj.enforcement.Application.user.profile.mailing_address_state,
                    obj.enforcement.Application.user.profile.mailing_address_zip,
                    obj.breech.name,
                    obj.date_created,
                    obj.status,
                    obj.date_resolved,
                    ' - '.join(['{} - {}.'.format(n.text, n.modified.strftime('%x')) for n in obj.notes.all()]),
                ]
            else:
                from annual_report_form.models import annual_report
                annual_report = annual_report.objects.filter(Property=obj.enforcement.Property).last()
                if annual_report is not None:
                    annual_report_date = annual_report.created
                else:
                    annual_report_date = '-'
                data = [
                    obj.enforcement.Property.streetAddress,
                    obj.enforcement.Property.parcel,
                    obj.enforcement.Property.structureType,
                    'Legacy application not in system',
                    obj.enforcement.Property.status[5:],
                    annual_report_date, # no annual report lookup
                    obj.enforcement.Property.applicant,
                    '', # org
                    '', # email
                    '', # phone
                    '', # mailing address
                    '', # mailing city
                    '', # mailing state
                    '', # mailing zip
                    obj.breech.name,
                    obj.date_created,
                    obj.status,
                    obj.date_resolved,
                    ' - '.join(['{} - {}.'.format(n.text, n.modified.strftime('%x')) for n in obj.notes.all()]),
                ]

            row = writer.writerow(data)

        return response
    export_as_csv_custom_action.short_description = 'Export as CSV'

class EnforcementAdmin(admin.ModelAdmin):
    inlines = [NoteInline,BreechTypesInlineAdmin]
    readonly_fields=('user','current_property_status', 'closing_info', 'find_takeback', 'open_breech_count', 'person', 'contact_info', 'last_sale_date', 'open_breech_types')
    #fields = ('breech_types',)
    list_filter = ('level_of_concern','open_breech_count')
    list_display = ('Property', 'person', 'last_sale_date', 'created', 'modified', 'level_of_concern', 'open_breech_count', 'open_breech_types')
    search_fields = ('Property__parcel', 'Property__streetAddress', 'Application__user__first_name','Application__user__last_name', 'Application__organization__name')

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(EnforcementAdmin, self).formfield_for_dbfield(db_field, **kwargs)

        if db_field.name == 'Application':
            formfield.queryset = Application.objects.none()
            # terrible? way to get object id if we are editting an existing object
            try:
                # http://stackoverflow.com/a/18318866/2731298 -- changed -1 to -2 to grab second to last argument in url since changed in django 1.11 I think
                obj_id = int([i for i in str(kwargs['request'].path).split('/') if i][-2])
            except ValueError:
                obj_id = None

            # If we are edding an existing Enforcement, restrict application choices if property selected
            if obj_id != None:
                obj = Enforcement.objects.get(id=obj_id)
                if obj.Property is not None: # and obj.Application is None:
                    formfield.queryset = Application.objects.filter(Property__exact=obj.Property)
        return formfield


    def person(self, obj):
        if obj.Application is not None:
            name = '{} {}'.format(obj.Application.user.first_name, obj.Application.user.last_name)
            if obj.Application.organization is not None:
                name = '{} ({})'.format(name, obj.Application.organization)
        else:
            name = obj.owner
        return name

    def contact_info(self, obj):
        if obj.Application is not None:
            email = obj.Application.user.email
            phone = obj.Application.user.profile.phone_number
            return '{} {}'.format(email, phone)
        return ''


    def last_sale_date(self, obj):
        if 'Sold' in obj.Property.status:
            return obj.Property.status[5:]
        return '-'


    def save_model(self, request, obj, form, change):
    #    if obj is None and obj.user is None:
    #        obj.user = request.user
        super(EnforcementAdmin, self).save_model(request, obj, form, change)

    def current_property_status(self, obj):
        if obj is not None and obj.Property is not None:
            return obj.Property.status
        else:
            return '-'


    def closing_info(self, obj):
        if obj is not None and obj.Application is not None:
            try:
                url = reverse("admin:closings_closing_change", args=(obj.Application.closing_set.first().id,) )
            except NoReverseMatch:
                pass
            else:
                closing_link = '<a target="_blank" href="{}">{}</a>'.format(
                    url,
                    obj.Application.closing_set.first().date_time
                )
                return mark_safe(closing_link)
        return 'No closing linked to application selected'

    def find_takeback(self, obj):
        if obj is not None and obj.Application is not None:
            try:
                url = reverse("admin:property_inventory_take_back_change", args=(take_back.objects.get(application=obj.Application).id,) )
            except NoReverseMatch:
                print('exceiption')
            else:
                tb_link = '<a target="_blank" href="{}">{}</a>'.format(
                    url,
                    obj.Application.closing_set.first().date_time
                )
                return mark_safe(tb_link)
        return 'No take back linked to application selected'

    def open_breech_types(self, obj):
        values = ''
        for b in obj.breech_types.filter(breechstatus__status=BreechStatus.OPEN):
            values = '{}{}/'.format(values, b)
        return values

class WorkoutMeetingAdmin(admin.ModelAdmin):
    inlines = [EnforcementInlineAdmin,]




class ReleaseAdmin(admin.ModelAdmin):
    inlines = [NoteInline,]
    raw_id_fields = ('Property','Application')
    search_fields = (
        'Property__streetAddress',
        'Property__parcel',
        'Application__Property__streetAddress',
        'Application__Property__parcel',
        'Inspection__request__Property__streetAddress',
        'Inspection__request__Property__parcel',
        'Inspection__request__Application__Property__streetAddress',
        'Inspection__request__Application__Property__parcel',

    )
    list_display = ('created', 'Inspection', 'Property', 'Application', 'owner', 'date_recorded')


admin.site.register(Document, DocumentAdmin)
admin.site.register(Note)
admin.site.register(Release, ReleaseAdmin)
admin.site.register(InspectionRequest, InspectionRequestAdmin)
admin.site.register(Inspection, InspectionAdmin)
admin.site.register(BreechType)
admin.site.register(BreechStatus, BreechStatusAdmin)
admin.site.register(Enforcement, EnforcementAdmin)
admin.site.register(WorkoutMeeting,WorkoutMeetingAdmin)
