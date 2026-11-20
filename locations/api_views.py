from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import mixins, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PickupLocation
from .serializers import NearbyItemSerializer, NearbyQuerySerializer, PickupLocationSerializer
from .services import nearby_items


@method_decorator(never_cache, name='dispatch')
class PickupLocationViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]
    serializer_class = PickupLocationSerializer
    pagination_class = None

    def get_queryset(self):
        return PickupLocation.objects.filter(owner=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])


@method_decorator(never_cache, name='dispatch')
class NearbyItemsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        query = NearbyQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        latitude = query.validated_data['latitude']
        longitude = query.validated_data['longitude']
        radius = query.validated_data['radius']
        items = nearby_items(latitude, longitude, radius)
        return Response({'items': NearbyItemSerializer(items, many=True).data, 'radius_km': radius})
