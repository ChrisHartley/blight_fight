# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import python_2_unicode_compatible
from os.path import basename
import pyclamd
from django.core.mail import send_mail
from PIL import Image, ExifTags
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

from property_inventory.models import Property
from applications.models import Application

@python_2_unicode_compatible
class Note(models.Model):
    content_type = models.ForeignKey(ContentType, related_name='pa_note_content_type', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    text = models.CharField(
        max_length=5000,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
#    user = models.ForeignKey(get_user_model(), related_name='pa_note_user', on_delete=models.CASCADE)

    def __str__(self):
        if len(self.text) > 17:
            elipse = '...'
        else:
            elipse = ''
        return '{}{} @ {}'.format(self.text[:20], elipse, self.modified.strftime('%c'))

@python_2_unicode_compatible
class Document(models.Model):
    content_type = models.ForeignKey(ContentType, related_name='pa_document_content_type', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey() #'content_type', 'object_id')
#    user = models.ForeignKey(get_user_model(), related_name='pa_document_user', on_delete=models.CASCADE)

    file = models.FileField(
        upload_to="documents/%Y/%m/%d", max_length=512)

    file_purpose = models.CharField(
        verbose_name='Briefly describe this file',
        blank=True,
        max_length=255
    )

    publish = models.BooleanField(default=False)
    is_photo = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super(Document, self).save(*args, **kwargs)
        try:
            cd = pyclamd.ClamdUnixSocket()
            # test if server is reachable
            cd.ping()
        except pyclamd.ConnectionError:
            # if failed, test for network socket
            cd = pyclamd.ClamdNetworkSocket()
        try:
            cd.ping()
        except pyclamd.ConnectionError:
            raise ValueError('could not connect to clamd server either by unix or network socket')

        scan_results = cd.scan_file(self.file.path)
        if scan_results is not None:
            send_mail('Django Virus Found', 'Virus found in file uploaded', 'info@renewindianapolis.org',
        ['chris.hartley@renewindianapolis.org'], fail_silently=False)
            return True
        try:
            im = Image.open(self.file.path)
            if im.verify() == True:
                self.is_photo = True
                # image rotation code from http://stackoverflow.com/a/11543365/2731298
                e = None
                if hasattr(im, '_getexif'): # only present in JPEGs
                    for orientation in list(ExifTags.TAGS.keys()):
                        if ExifTags.TAGS[orientation]=='Orientation':
                            break
                    e = im._getexif()       # returns None if no EXIF data
                if e is not None:
                    exif=dict(list(e.items()))
                    orientation = exif.get(orientation, None)
                    if orientation == 3:   im = im.transpose(Image.ROTATE_180)
                    elif orientation == 6: im = im.transpose(Image.ROTATE_270)
                    elif orientation == 8: im = im.transpose(Image.ROTATE_90)
    #            im.thumbnail((1024,1024))
                im.save(self.file.path)
        except:
            return False

    def __str__(self):
        return '{} - {}'.format(basename(self.file.name), self.file_purpose[:20] )


class Release(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    Property = models.ForeignKey(Property, null=True, blank=True, on_delete=models.CASCADE)
    Application = models.ForeignKey(Application, null=True, blank=True, on_delete=models.CASCADE)
    owner = models.CharField(max_length=254, blank=True, help_text='Used only if property was sold with a legacy application not in the system')

    Inspection = models.ForeignKey('Inspection', blank=False, null=False, on_delete=models.CASCADE)

    instrument_number = models.CharField(max_length=254, blank=True)
    recorded_document = models.ForeignKey(Document, blank=True, null=True, on_delete=models.CASCADE)
    date_recorded = models.DateField(null=True, blank=True)
    def __str__(self):
        prop = 'none'
        if self.Property is not None:
            prop = self.Property
        elif self.Application is not None:
            prop = self.Application.Property
        elif self.Inspection is not None:
            prop = self.Inspection
        return '{}, Instrument Number: {}, Date: {}'.format(prop, self.instrument_number, self.date_recorded )

    def save(self, *args, **kwargs):
        super(Release, self).save(*args, **kwargs)
        prop = None
        if self.Property is not None:
            prop = self.Property
        elif self.Application is not None and self.Application.Property is not None:
            prop = self.Application.Property
        elif self.Inspection is not None and self.Inspection.request is not None and self.Inspection.request.Property:
            prop = self.Inspection.request.Property
        elif self.Inspection is not None and self.Inspection.request is not None and self.Inspection.request.Application is not None and self.Inspection.request.Application.Property is not None:
            prop = self.Inspection.request.Application.Property
        if prop is not None and prop.project_agreement_released == False and self.date_recorded is not None:
            prop.project_agreement_released = True
            prop.save()


class InspectionRequest(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    datetime = models.DateTimeField(null=True, blank=True, help_text="Scheduled date/time")
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE,  null=True, blank=True)
    notes = GenericRelation(Note, related_name='inspectionrequest_notes')
    documents = GenericRelation(Document, related_name='inspectionrequest_documents')

    Property = models.ForeignKey(Property, null=True, blank=True, on_delete=models.CASCADE)
    Application = models.ForeignKey(Application, null=True, blank=True, on_delete=models.CASCADE)
    owner = models.CharField(max_length=254, blank=True, help_text='Used only if property was sold with a legacy application not in the system')

    email = models.CharField(max_length=254, blank=True, help_text='Enter your email address if the one tied to your account is not accurate')
    phone_number = models.CharField(max_length=15, blank=True, help_text='Enter your phone number if the one tied to your account is not accurate')
    request_notes = models.CharField(max_length=254, blank=True, help_text="Any notes for the inspector before they contact you?")

    def __str__(self):
        if self.pk is not None:
            if self.Property is not None:
                prop = self.Property
            elif self.Application is not None:
                prop = self.Application.Property
            else:
                prop = None

            if self.owner != '':
                person = self.owner
            elif self.Application is not None:
                if self.Application.organization is not None:
                    org = self.Application.organization.name
                else:
                    org = None
                person = '{} {} ({})'.format(self.Application.user.first_name, self.Application.user.last_name, org)
            else:
                person = None
        else:
            prop = None
            person = None

        return '{} - {}'.format(prop, person)

    def save(self, *args, **kwargs):
        new = (self.id is None)
        contact = None
        prop = None
        if self.Property is not None:
            prop = self.Property
        elif self.Application is not None and self.Application.Property is not None:
            prop = self.Application.Property
        if prop.renew_owned == True:
            contact = settings.COMPANY_SETTINGS['RENEW_PA_RELEASE']
        elif prop.renew_owned == False:
            contact = settings.COMPANY_SETTINGS['CITY_PA_RELEASE']
        if new == True and contact is not None and prop is not None:
            send_mail(
                'Inspection Request Submitted - {}'.format(prop,),
                'An inspection request has been submitted for the property at {}. Please take a look: https://build.renewindianapolis.org{}'.format(prop, reverse('admin:project_agreement_management_inspectionrequest_change', args=(self.id,) )),
                'info@renewindianapolis.org',
                [contact,],
                fail_silently=False
            )
        if self.Property is not None and self.Application is None and self.Property.buyer_application is not None:
            self.Application = self.Property.buyer_application

        super(InspectionRequest, self).save(*args, **kwargs)


# class InspectionRequestPhotoSet(models.Model):
#     Exterior:
#
#     exterior_front
#     exterior_rear
#     exterior_side1
#     exterior_side2
#
#     interior_entry
#     interior_family_room
#     interior_dining_room
#     interior_kitchen
#     interior_bathroom1
#
#
# Interior:
#
#     Entry
#     Family/Living room
#     Dining room
#     Kitchen
#     Bathrooms
#     Bedrooms
#     Basement (if applicable)
#
#
#
# Other Items:
#
#     Electrical Panel
#     Furnace
#     Water Heater

class Inspection(models.Model):

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    datetime = models.DateTimeField(null=True, blank=True, help_text="Scheduled date/time")
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    notes = GenericRelation(Note)
    documents = GenericRelation(Document)
    request = models.ForeignKey(InspectionRequest, blank=False, null=False)
    pass_outcome = models.NullBooleanField(blank=True, null=True)

    def __str__(self):
        return '{} - Pass: {} - Release in place: {}'.format(self.request, self.pass_outcome, self.release_set.count()>0)


class BreechType(models.Model):
    name = models.CharField(max_length=254, blank=False, null=False)
    description = models.CharField(max_length=254, blank=True, null=False)

    def __str__(self):
        return '{}'.format(self.name,)


class Enforcement(models.Model):

    LOW_CONCERN = 1
    MEDIUM_CONCERN = 2
    HIGH_CONCERN = 3
    IMMEDIATE_CONCERN = 4

    CONCERN_CHOICES = [
        (LOW_CONCERN, 'Low concern'),
        (MEDIUM_CONCERN, 'Medium concern'),
        (HIGH_CONCERN, 'High concern'),
        (IMMEDIATE_CONCERN, 'Immediate concern'),
    ]

    Property = models.ForeignKey(
        Property,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Select a property first",
        )
    Application = models.ForeignKey(
        Application,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Select the application that went with the sale of the property",

        )

    owner = models.CharField(
        max_length=254,
        blank=True,
        help_text='Used only if property was sold with a legacy application not in the system'
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, blank=True, null=True)
    notes = GenericRelation(Note)
    documents = GenericRelation(Document)

    level_of_concern = models.PositiveIntegerField(
        blank=True,
        choices=CONCERN_CHOICES,
        null=True
    )

    breech_types = models.ManyToManyField(BreechType, blank=True, through='BreechStatus')
    meeting = models.ManyToManyField('WorkoutMeeting', blank=True)

    open_breech_count = models.PositiveIntegerField(blank=True, null=False, default=0)

    def save(self, *args, **kwargs):
        super(Enforcement, self).save(*args, **kwargs)

    def __str__(self):
        person = self.owner if self.Application is None else '{} {} ({})'.format(self.Application.user.first_name, self.Application.user.last_name, self.Application.organization)
        return '{} - {} - {} - {}'.format(self.Property, person, self.created.strftime('%x'), self.get_level_of_concern_display())

class BreechStatus(models.Model):
    CLOSED = True
    OPEN = False

    RESOLVED_CHOICES = [
        (CLOSED, 'Closed'),
        (OPEN, 'Open')

    ]

    breech = models.ForeignKey(BreechType, on_delete=models.CASCADE)
    enforcement = models.ForeignKey(Enforcement, on_delete=models.CASCADE)
    date_created = models.DateField(blank=False)
    status = models.BooleanField(choices=RESOLVED_CHOICES, default=False)
    date_resolved = models.DateField(blank=True, null=True)

    notes = GenericRelation(Note)
    documents = GenericRelation(Document)

    def save(self, *args, **kwargs):
        old = BreechStatus.objects.filter(pk=getattr(self,'pk',None)).first()
        if old:
            print(old)
            if old.status == self.OPEN and self.status == self.CLOSED:
                self.enforcement.open_breech_count = self.enforcement.open_breech_count - 1
            elif old.status == self.CLOSED and self.status == self.OPEN:
                self.enforcement.open_breech_count = self.enforcement.open_breech_count + 1

        else:
            if self.status == self.OPEN:
                self.enforcement.open_breech_count = self.enforcement.open_breech_count + 1

        self.enforcement.save()
        if self.status == self.CLOSED and self.date_resolved is None:
            self.date_resolved = timezone.now()

        super(BreechStatus, self).save(*args, **kwargs)


    class Meta:
        verbose_name = 'breech status'
        verbose_name_plural = 'breech statuses'

    def __str__(self):
        return '{} {} {}'.format(self.breech, self.date_created.strftime('%x'), self.get_status_display())

class WorkoutMeeting(models.Model):
    datetime = models.DateTimeField(null=True, blank=True, help_text="Scheduled date/time")

    def __str__(self):
        return 'Workout - {}'.format(self.datetime.strftime('%b %d, %Y'),)

    # Date and time
    # Created
    # Enforcements can be linked many to many
    #
