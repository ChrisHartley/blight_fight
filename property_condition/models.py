from django.db import models
from PIL import Image
from django.conf import settings
from django.db.models import Q
#from property_inventory.models import Property
from django.utils.encoding import python_2_unicode_compatible



@python_2_unicode_compatible
class Room(models.Model):
    ROOM_TYPE_CHOICES = (
        ('ATCFN','Attic, Finished'),
        ('ENBAL','Balcony, Enclosed'),
        ('MSTBD','MasterBedroom'),
        ('2BDRM','Bedroom 2nd'),
        ('3BDRM','Bedroom 3rd'),
        ('4BDRM','Bedroom 4th'),
        ('5BDRM','Bedroom 5th'),
        ('6BDRM','Bedroom 6th'),
        ('BONUS','BonusRoom'),
        ('BKFST','BreakfastRoom'),
        ('DENLB','DenLibrary'),
        ('DIN','DiningRoom'),
        ('EXRCS','ExerciseRm'),
        ('FAMLY','FamilyRoom'),
        ('GREAT','GreatRoom'),
        ('GUEST','GuestRoom'),
        ('HERTH','HearthRoom'),
        ('HMTHR','HomeTheatr'),
        ('KITCH','Kitchen'),
        ('LNDRY','LaundryRm'),
        ('LIVNG','LivingRoom'),
        ('LOFT','Loft'),
        ('MUDRM','MudRoom'),
        ('OFFIC','Office'),
        ('RECRM','Rec\/PlayRm'),
        ('SITRM','SittingRoom'),
        ('SUNRM','SunRoom'),
        ('UTILITY','Utility Room'),
        ('WINEC','WineCellar'),
        ('WRKSH','Workshop'),
    )
    room_type = models.CharField(choices=ROOM_TYPE_CHOICES, blank=False, null=False, max_length=254)

    LEVEL_CHOICES = (
        ('BASEMENT', 'Basement'),
        ('LOWER', 'Lower'),
        ('MAIN', 'Main'),
        ('UPPER', 'Upper'),
    )

    room_level = models.CharField(choices=LEVEL_CHOICES, blank=False, null=False, max_length=254)

    FLOORING_TYPE = (
        ('B','Brick'),
        ('C','Carpeting'),
        ('H','Hardwood'),
        ('L','Laminate'),
        ('LH','Laminated Hardwood'),
        ('M','Marble'),
        ('P','Parquet'),
        ('T','Tile-Ceramic'),
        ('V','Vinyl'),
        ('VinylHardwood','Vinyl Hardwood'),
        ('O','Other')
    )

    flooring_type = models.CharField(choices=FLOORING_TYPE, blank=False, null=False, max_length=254)
    dimensions = models.CharField(max_length=50, blank=True, null=False)
    conditionreport = models.ForeignKey('property_condition.ConditionReport', on_delete=models.CASCADE)

    def __str__(self):
        return '{0} - {1}'.format(self.conditionreport, self.get_room_type_display())

def content_file_name(instance, filename):
    address = 'No Address'
    if instance.Property is not None:
        address = instance.Property.streetAddress
    elif instance.Property_ncst is not None:
        address = instance.Property_ncst.street_address
    elif instance.Property_surplus is not None:
        address = instance.Property_surplus.street_address

    path = '/'.join(['condition_report', address, filename])
    return path

@python_2_unicode_compatible
class ConditionReport(models.Model):

    GOOD_STATUS = 3
    FAIR_STATUS = 2
    POOR_STATUS = 1
    MISSING_STATUS = 0
    NA_STATUS = None

    STATUS_CHOICES = (
        (GOOD_STATUS, 'Good / Satisfactory'),
        (FAIR_STATUS, 'Fair / Repair'),
        (POOR_STATUS, 'Poor / Replace'),
        (MISSING_STATUS, 'Missing'),
        (NA_STATUS, 'N/A'))

    def limit_property_choices():
        return Q( (Q(structureType__exact='Residential Dwelling') | Q(structureType__exact='Mixed Use Commercial')), ~Q(status__contains='Sold'))

    Property = models.ForeignKey('property_inventory.Property', limit_choices_to=limit_property_choices(), null=True, blank=True, on_delete=models.CASCADE)
    Property_ncst = models.ForeignKey('ncst.Property', null=True, blank=True, on_delete=models.CASCADE)
    Property_surplus = models.ForeignKey('surplus.parcel', null=True, blank=True, on_delete=models.CASCADE)

    picture = models.ImageField(upload_to=content_file_name, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


    general_property_notes = models.CharField(
        max_length=5000, blank=True, verbose_name='General Property Notes')


    secure = models.NullBooleanField(null=True, blank=True, help_text='Property is secured')
    occupied = models.NullBooleanField(null=True, blank=True, help_text='Property is occupied as long term residence')
    major_structural_issues = models.NullBooleanField(null=True, blank=True, help_text='Are there major structural issues, eg roof holes, foundation collapse?')
    quick_condition =  models.IntegerField(null=True, blank=True, help_text='On a scale of 1-10 (bad-good) what is the property?')

    roof_shingles = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Shingles')
    roof_shingles_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    roof_framing = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Framing')
    roof_framing_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    roof_gutters = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Gutters')
    roof_gutters_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    foundation_slab = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Slab')
    foundation_slab_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    foundation_crawl = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Crawlspace')
    foundation_crawl_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    exterior_siding_brick = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Brick')
    exterior_siding_brick_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    exterior_siding_vinyl = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Vinyl')
    exterior_siding_vinyl_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    exterior_siding_wood = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Wood')
    exterior_siding_wood_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    exterior_siding_other = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Other')
    exterior_siding_other_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    windows = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Windows')
    windows_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    garage = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Garage')
    garage_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    fencing = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Fencing')
    fencing_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    landscaping = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Landscaping')
    landscaping_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    doors = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Doors')
    doors_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    kitchen_cabinets = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Kitchen Cabinets')
    kitchen_cabinets_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    flooring_subflooring = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Subflooring')
    flooring_subflooring_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    flooring_covering = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Covering')
    flooring_covering_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    electrical_knob_tube_cloth = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Knob, tube and cloth')
    electrical_knob_tube_cloth_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    electrical_standard = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Standard')
    electrical_standard_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    plumbing_metal = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Copper / metal')
    plumbing_metal_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    plumbing_plastic = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='PVC / PEX')
    plumbing_plastic_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    walls_drywall = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Drywall')
    walls_drywall_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    walls_lathe_plaster = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Plaster and lathe')
    walls_lathe_plaster_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    hvac_furance = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Furnace')
    hvac_furance_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    hvac_duct_work = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='Duct work')
    hvac_duct_work_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')
    hvac_air_conditioner = models.IntegerField(
        choices=STATUS_CHOICES, null=True, blank=True, verbose_name='AC')
    hvac_air_conditioner_notes = models.CharField(
        max_length=512, blank=True, verbose_name='Notes')

    scope_of_work = models.FileField(blank=True)


    def save(self, size=(400, 300)):
        """
        Save Photo after ensuring it is not blank.  Resize as needed.
        """
        #print "Does the object already exist?", self.id
        super(ConditionReport, self).save()

        # if self.picture:
        #     filename = self.picture.path
        #     image = Image.open(filename)
        #     if image.size[0] > 1024:
        #         image.thumbnail(size, Image.ANTIALIAS)
        #         image.save(filename)

    def __str__(self):
        return '{0} - {1}'.format(self.Property or self.Property_ncst or self.Property_surplus or 'no_property', self.timestamp)



class ConditionReportProxy(ConditionReport):
    class Meta:
        proxy = True
