from django.core.management.base import BaseCommand, CommandError
from property_inquiry.models import propertyInquiry
from django.contrib.auth.models import User
from datetime import timedelta, datetime, date
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Q
from property_inventory.models import Property
from applications.models import Application
from project_agreement_management.models import Enforcement, BreechType, BreechStatus

class Command(BaseCommand):
    help = 'Check for properties past the two year deadline and create enforcements and breeches'
    deadline = timedelta(days=(2*365))


    def handle(self, *args, **options):
        props = Property.objects.filter(project_agreement_released=False).filter(status__startswith='Sold')

        overdue_breech = BreechType.objects.get(name='Past two year deadline')

        for p in props:
            sold_date = datetime.strptime(p.status[5:], "%m/%d/%Y").date()
            if sold_date + self.deadline <= date.today():
                app = p.buyer_application
                if app is not None:
                    if app.application_type not in[Application.HOMESTEAD, Application.STANDARD]:
                        self.stdout.write('No timeline in PA. Property: {}, Application: {}, Application Type: {}'.format(p, app, app.application_type))
                        continue
                    enforcements = Enforcement.objects.filter(Property=p).filter(Application=app).order_by('created')
                else:
                    enforcements = Enforcement.objects.filter(Q(Application__isnull=True) & Q(owner__exact=p.applicant))
                has_overdue = False
                for e in enforcements:
                        for b in e.breech_types.all():
                            if b == overdue_breech:
                                has_overdue = True
                if has_overdue == False:
                    self.stdout.write('Overdue breech created for {}'.format(p,))
                    enf = enforcements.last()
                    if enf is None:
                        if app is not None:
                            enf = Enforcement(Property=p, Application=app)
                        else:
                            enf = Enforcement(Property=p, owner=p.applicant)
                        enf.save()
                    bs = BreechStatus(breech=overdue_breech, enforcement=enf, date_created=date.today())
                    bs.save()
