import django_tables2 as tables2
from django_tables2_reports.tables import TableReport
from django_tables2.utils import A

from .models import Organization
from applications.models import Application
from property_inquiry.models import propertyInquiry
from property_inventory.models import Property

class OrganizationTable(TableReport):

	class Meta:
		model = Organization
		attrs = {"class": "table table-bordered"}
		fields = ("name",)
		#sequence = ("id", "street_address", "parcel", "inquiry_count", "...")

class ApplicationTable(TableReport):
	structure_type = tables2.Column(accessor='Property.structureType')
	#detail_link = tables2.LinkColumn('process_application', args=[A('id')], kwargs='edit', verbose_name='Edit', empty_values=())

	class Meta:
		model = Application
		attrs = {"class": "table table-bordered"}
		fields = ("Property", "structure_type", "status",)

class PropertyInquiryTable(TableReport):

	class Meta:
		model = propertyInquiry
		attrs = {"class": "table table-bordered"}
		fields = ("Property", "timestamp",)