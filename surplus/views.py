from django.shortcuts import render
from django.views.generic import DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.gis.serializers.geojson import Serializer as GeoJSONSerializer
from django.forms.models import model_to_dict
from djqscsv import render_to_csv_response

from .models import Parcel
from .filters import SurplusParcelFilter
from django.http import JsonResponse, HttpResponse
from django.core import serializers

class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    https://docs.djangoproject.com/en/1.8/topics/class-based-views/generic-editing/
    """
    def form_invalid(self, form):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.request.is_ajax():
            return JsonResponse(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return JsonResponse(data)
        else:
            return response


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        return JsonResponse(
            self.get_data(context),
            **response_kwargs
        )

    def get_data(self, context):
        """
        Returns an object that will be serialized as JSON by json.dumps().
        """
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return model_to_dict(context)

class ParcelDetailView(JSONResponseMixin, DetailView):
    model = Parcel
    slug_field = 'parcel_number'
    slug_url_kwarg = 'parcel'
    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)

class ParcelListView(ListView):
    model = Parcel

class ParcelUpdateView(AjaxableResponseMixin, UpdateView):
    model = Parcel
    fields = ['interesting','notes']

class SurplusMapTemplateView(TemplateView):
    template_name = "surplus_map_fancy_three.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(SurplusMapTemplateView, self).dispatch(*args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(SurplusMapTemplateView, self).get_context_data(**kwargs)
        context['filter'] = SurplusParcelFilter
        return context


class DisplayNameJsonSerializer(GeoJSONSerializer):

    def handle_field(self, obj, field):
        value = field._get_val_from_obj(obj)

        display_method = "get_%s_display" % field.name
        if hasattr(obj, display_method):
            self._current[field.name] = getattr(obj, display_method)()
        elif is_protected_type(value):
            self._current[field.name] = value
        else:
            if field == "price":
                self._current[field.name] = "$".join(
                    field.value_to_string(obj))
            else:
                self._current[field.name] = field.value_to_string(obj)





@ensure_csrf_cookie
def searchSurplusProperties(request):
    #	config = RequestConfig(request)
    f = SurplusParcelFilter(request.GET, queryset=Parcel.objects.exclude(area__lte=500))
    geom = 'geometry'
    #serializers.register_serializer('geojson_display', DisplayNameJsonSerializer)
    #json_serializer = DisplayNameJsonSerializer()

    if request.GET.get("geometry_type") == "centroid":
        geom = 'centroid_geometry'
    #s = serializers.serialize('geojson_display',
    s = json_serializer.seralize('geojson',
        f.qs,
        geometry_field=geom,
        srid=2965,
        fields=('parcel_number','street_address', 'zipcode', 'zoning',
            'township', 'has_building', 'land_value', 'improved_value',
            'area', 'assessor_classification', 'classification',
            'interesting', 'notes', geom),
        use_natural_foreign_keys=True
    )
    return HttpResponse(s, content_type='application/json')

@csrf_exempt
def surplusUpdateFieldsFromMap(request):
    prop = Parcel.objects.get(parcel_number=request.POST.get('parcel_number', None))
    if request.POST.get('notes', None):
        print request.POST.get('notes', None)
        prop.notes = request.POST.get('notes')
    if request.POST.get('interesting', None) == 'on':
        prop.interesting = True
    else:
        prop.interesting = False
    try:
        prop.save()
        return JsonResponse({'status': 'OK'})
    except:
        return JsonResponse({'status':'Not OK'})


def get_surplus_inventory_csv(request):
    qs = Parcel.objects.all().values('parcel_number','street_address','township','zipcode','zoning','has_building','improved_value','land_value','area','assessor_classification','classification','demolition_order','repair_order','interesting','notes') #.values('parcel', 'street_address')
    #qs = Property.objects.all().prefetch_related('cdc', 'zone', 'zipcode')
    return render_to_csv_response(qs)
