from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from datetime import timedelta, datetime, date
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from property_inventory.models import Property
from project_agreement_management.models import Enforcement, BreechType, BreechStatus

class Command(BaseCommand):
    help = 'Check for released properties with open breeches and close as necessary'
    #deadline = timedelta(days=(2*365))


    def add_arguments(self, parser):
#        parser.add_argument('parcels', nargs='+')
        parser.add_argument(
            '--fake',
            action='store_true',
            dest='fake',
            default=False,
            help="Don't actually close breeches, just show which would be closed.",
        )


    def handle(self, *args, **options):
        props = Property.objects.filter(project_agreement_released=True).filter(status__startswith='Sold')

        tax_delinquent = BreechType.objects.get(name='Delinquent Taxes')

        all_enf = Enforcement.objects.filter(Property__in=props)
        for e in all_enf:
        #    print(e.breech_types)
        #    print(dir(e))
            for b in e.breechstatus_set.all():
                if b.status == BreechStatus.OPEN:
                    print('{} - Breach is open property was released, should be closed'.format(e,))
                    b.date_resolved = timezone.now()
                    b.status = BreechStatus.CLOSED
                    if options['fake'] == False:
                        b.save()
                    else:
                        print('Not saving due to --fake')
