import django_filters
from django_filters.widgets import RangeWidget
from .models import Parcel
from django.db.models import Q
from django.contrib.gis.db import models

from .forms import SurplusSearchForm

class SurplusParcelFilter(django_filters.FilterSet):
    #street_address = django_filters.CharFilter(lookup_type='icontains')
    #notes = django_filters.CharFilter(lookup_type='icontains')
    notes = django_filters.CharFilter()
    general_search = django_filters.CharFilter(method='general_search_filter')
    area = django_filters.RangeFilter(widget=RangeWidget(attrs={'placeholder': 'sqft'}))
    #area = django_filters.RangeFilter(name='area')
    has_building = django_filters.BooleanFilter(label='Has a structure')
    township = django_filters.MultipleChoiceFilter(choices=Parcel.TOWNSHIP_CHOICES)
    land_value = django_filters.RangeFilter(widget=RangeWidget(attrs={'placeholder': '$'}))
    improved_value = django_filters.RangeFilter(widget=RangeWidget(attrs={'placeholder': '$'}))
    interesting = django_filters.BooleanFilter()
    #parcel_number = django_filters.CharFilter(lookup_type='startswith')

    def general_search_filter(self, queryset, name, value):
        print "in general_search_filter"
        return queryset.filter(
             Q(street_address__icontains=value) |
            Q(zipcode__exact=value) |
            Q(parcel_number__exact=value)
            )

    class Meta:
        model = Parcel
        form = SurplusSearchForm
        exclude = ['centroid_geometry', 'geometry']

        filter_overrides = {
            models.MultiPolygonField: {
                'filter_class': django_filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'exact',
                }
            },
        }
