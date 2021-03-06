# -*- coding: utf-8 -*-


from django.contrib.gis.db import models
from localflavor.us.models import PhoneNumberField
from django.utils.encoding import python_2_unicode_compatible
from utils.utils import pull_property_info_from_arcgis
from photos.models import photo
from property_condition.models import ConditionReport
from django.apps import apps
from django.core.mail import EmailMessage
from django.conf import settings

@python_2_unicode_compatible
class Contact(models.Model):
    name = models.CharField(max_length=254, blank=False)
    phone = PhoneNumberField()
    email = models.EmailField(blank=True, default='')
    notes = models.CharField(blank=True, max_length=1024)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Program(models.Model):
    name = models.CharField(max_length=254, blank=False)
    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Seller(models.Model):
    name = models.CharField(max_length=254, blank=False)
    def __str__(self):
        return self.name


def save_location(instance, filename):
    if instance.parcel:
        return 'ncst/{0}/{1}'.format(instance.parcel, filename)
    return 'ncst/{0}/{1}'.format('no_parcel', filename)

@python_2_unicode_compatible
class Property(models.Model):
    NEW_STATUS = 1
    INSPECTING_STATUS = 2
    WAITING_OFFER_STATUS =  3
    OFFER_STATUS = 4
    PENDING_OFFER_ACCEPT_STATUS = 5
    OFFER_ACCEPT_STATUS = 6
    DECLINED_STATUS = 7
    REMOVED_STATUS = 8
    SENT_TO_DOC_PREP = 9
    NSI_AWAITING_PA = 10
    NSI_CLOSING = 11
    NSI_CLOSED = 12
    NST_TRIAGE_REVIEW = 13
    NSI_BUYER_EXECUTED_PA = 14
    CF_PROPERTY_LISTED = 15
    CF_EXPRESSED_INTEREST = 16
    CF_REMOVED = 17


    STATUS_CHOICES = (
        (NEW_STATUS, 'NSI New'),
        (INSPECTING_STATUS,'NSI Inspecting'),
        (WAITING_OFFER_STATUS,'NSI Awaiting Offer'),
        (OFFER_STATUS,'NSI Offer'),
        (PENDING_OFFER_ACCEPT_STATUS,'NSI Pending Offer Accept'),
        (NST_TRIAGE_REVIEW,'NSI Triage Review'),
        (OFFER_ACCEPT_STATUS,'NSI Offer Accepted'),
        (SENT_TO_DOC_PREP,'Sent to Doc Prep'),
        (NSI_AWAITING_PA,'NSI Awaiting PA'),
        (NSI_BUYER_EXECUTED_PA,'NSI Buyer Executed PA'),
        (NSI_CLOSING,'NSI Closing'),
        (NSI_CLOSED,'NSI Closed'),
        (DECLINED_STATUS,'NSI Declined by Buyer'),
        (REMOVED_STATUS,'NSI Removed by Seller'),
        (CF_PROPERTY_LISTED, 'CF - Property Listed'),
        (CF_EXPRESSED_INTEREST, 'CF - Expressed Interest'),
        (CF_REMOVED, 'CF - Removed by Seller or Expired'),
    )

    geometry = models.MultiPolygonField(srid=4326, blank=True, null=True)
    street_address = models.CharField(blank=True, max_length=254)
    city = models.CharField(blank=True, max_length=254, default='Indianapolis')
    zipcode = models.CharField(blank=True, max_length=5)
    parcel = models.CharField(blank=False, max_length=7)

    update_from_server = models.BooleanField(default=True, help_text="Attempt to update street address, etc from remote server on next save.")

    program = models.ForeignKey(Program, null=False, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, null=False, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.CASCADE)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    status = models.IntegerField(choices=STATUS_CHOICES, null=False, default=NEW_STATUS)

    lockbox =  models.CharField(blank=True, max_length=30)

    notes = models.CharField(blank=True, max_length=1024)

    closing_date = models.DateTimeField(blank=True, null=True)
    title_company = models.ForeignKey('closings.title_company', blank=True, null=True, on_delete=models.CASCADE)
    closed = models.BooleanField(
        default=False,
        blank=False,
    )

    convert_to_landbank_inventory_on_save = models.BooleanField(
        default=False,
        blank=False,
        verbose_name='Add property to landbank inventory and transfer photos and condition report'
    )


    price_efmv = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_adjustment = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_offer = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    request_deadline = models.DateTimeField(blank=False)
    inspection_deadline = models.DateTimeField(blank=True, null=True)
    acquisition_deadline = models.DateTimeField(blank=True, null=True)

    inspection_time = models.DateTimeField(blank=True, null=True, help_text='Start of window for inspection')

    recommendation = models.NullBooleanField(blank=True, help_text="Recommened by staff for acquisition?")

    market_assessment_spreadsheet = models.FileField(upload_to=save_location, blank=True, null=True)
    comparative_market_analysis = models.FileField(upload_to=save_location, blank=True, null=True)

    rehab_start_date = models.DateField(blank=True, null=True)
    rehab_end_date = models.DateField(blank=True, null=True)
    rehab_costs = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    holding_costs_at_sale = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"

    def __str__(self):
        return '{} - {}'.format(self.street_address, self.parcel)


    def save(self, *args, **kwargs):
        if self.update_from_server == True:
            results = pull_property_info_from_arcgis(self.parcel, request_type='json')
            if results:
                self.street_address = results['street_address']
                self.zipcode = results['zipcode']
                self.geometry = results['geometry']
                self.update_from_server = False


        if self.id is None:
            email = EmailMessage(
                'New NCST: {} - {}'.format(self.street_address, self.parcel),
                'A new NCST property at {} - parcel {} has been added to Blight Fight.'.format(self.street_address, self.parcel),
                'info@renewindianapolis.org',
                settings.COMPANY_SETTINGS['NCST_CONTACTS'],
                reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
            )
            email.send()


        if self.convert_to_landbank_inventory_on_save:
            inventory_property_model = apps.get_model('property_inventory', 'Property')

            p, created = inventory_property_model.objects.get_or_create(
                parcel=self.parcel,
                defaults={
                    'update_from_server': True,
                    'status': 'New NCST acquisition',
                    'renew_acquisition_date': self.closing_date,
                    'renew_owned': True,
                },
            )
            p.save()
            phs = photo.objects.filter(prop_ncst=self)
            for ph in phs:
                ph.prop = p
                ph.prop_ncst = None
                ph.save()
            condition_reports = ConditionReport.objects.filter(Property_ncst=self)
            for condition_report in condition_reports:
                condition_report.Property = p
                condition_report.Property_ncst = None
                condition_report.save()
            self.convert_to_landbank_inventory_on_save = False

        if self.id is not None:
            existing = Property.objects.filter(id=self.id).first()
            if existing is not None:
                if existing.rehab_start_date is None and self.rehab_start_date is not None:
                    email = EmailMessage(
                        'NCST rehab start: {} - {}'.format(self.street_address, self.parcel),
                        'Rehab work started on {0} for the NCST property at {1} - parcel {2}. Update insurance as necessary.'.format(self.rehab_start_date, self.street_address, self.parcel),
                        'info@renewindianapolis.org',
                        settings.COMPANY_SETTINGS['RENEW_REHAB_CONTACT'],
                        reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
                    )
                    email.send()
                # if existing.rehab_end_date is None and self.rehab_end_date is not None:
                #     email = EmailMessage(
                #         'NCST rehab end: {} - {}'.format(self.street_address, self.parcel),
                #         'Rehab work completed on {0} for the NCST property at {1} - parcel {2}. Update insurance as necessary.'.format(self.rehab_end_date, self.street_address, self.parcel),
                #         'info@renewindianapolis.org',
                #         settings.COMPANY_SETTINGS['RENEW_REHAB_CONTACT'],
                #         reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
                #     )
                #     email.send()

                if existing.closed == False and self.closed == True:
                    email = EmailMessage(
                        'NCST property purchased: {} - {}'.format(self.street_address, self.parcel),
                        'The NCST property at {} - parcel {} was purchased.'.format(self.street_address, self.parcel),
                        'info@renewindianapolis.org',
                        ['chartley@renewindy.org','bburns@renewindy.org'],
                        reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
                    )
                    email.send()

                if existing.market_assessment_spreadsheet == '' and self.market_assessment_spreadsheet != '':
                    email = EmailMessage(
                        'NCST market assessment tool spreadsheet uploaded: {} - {}'.format(self.street_address, self.parcel),
                        'The NCST property at {} - parcel {} had a market assessment tool spreadsheet uploaded.'.format(self.street_address, self.parcel),
                        'info@renewindianapolis.org',
                        ['realestateteam@renewindy.org ',], # need to notify everyone
                        reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
                    )
                    email.send()

                if existing.lockbox == '' and self.lockbox != '':
                    email = EmailMessage(
                        'NCST property lockbox info added: {} - {}'.format(self.street_address, self.parcel),
                        'The NCST property at {} - parcel {} had a lockbox code of {} entered.'.format(self.street_address, self.parcel, self.lockbox),
                        'info@renewindianapolis.org',
                        ['realestateteam@renewindy.org ',], # need to notify everyone
                        reply_to=[settings.COMPANY_SETTINGS['APPLICATION_CONTACT_EMAIL']]
                    )
                    email.send()




        super(Property, self).save(*args, **kwargs)
