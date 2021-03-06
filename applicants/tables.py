import django_tables2 as tables2
from django_tables2.utils import A

from .models import Organization
from applications.models import Application
from property_inquiry.models import propertyInquiry
from property_inventory.models import Property


class OrganizationTable(tables2.Table):
    edit_org = tables2.LinkColumn(
        'applicants_organization_edit',
        kwargs={
            'id': A('id'),
        },
        text='edit',
        empty_values=(),
    )

    class Meta:
        model = Organization
        attrs = {"class": "table table-bordered"}
        fields = ("name", "phone_number", "mailing_address_city")
        #sequence = ("id", "street_address", "parcel", "inquiry_count", "...")


class ApplicationTable(tables2.Table):
    structure_type = tables2.Column(accessor='Property.structureType')
    #detail_link = tables2.LinkColumn('process_application', args=[A('id')], kwargs='edit', verbose_name='Edit', empty_values=())
    edit_app = tables2.LinkColumn(
        'process_application',
        kwargs={
            'action': 'edit',
            'id': A('id'),
        },
        text='edit',
        empty_values=(),
    )

    class Meta:
        model = Application
        attrs = {"class": "table table-bordered"}
        fields = ("Property", "structure_type", "status", "edit_app",)


class PropertyInquiryTable(tables2.Table):
    requested_timestamp = tables2.Column(
        accessor='timestamp', verbose_name="Submitted")

    class Meta:
        model = propertyInquiry
        attrs = {"class": "table table-bordered"}
        fields = ("Property", "requested_timestamp",)


class PropertiesUnderPATable(tables2.Table):
    request_release = tables2.LinkColumn(
        'pa_release_inspection_request_parcel',
        kwargs={
            'parcel': A('parcel'),
        },
        text='Request Release Inspection',
        empty_values=(),
    )
    class Meta:
        model = Property
        attrs = {"class": "table table-bordered"}
        fields = ("streetAddress", "parcel", "structureType", "status", "project_agreement_released", "request_release",)
