from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Category
from .serializers import CategorySerializer


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
def category_list(request):
    if request.method in ("GET", "POST"):
        categories = Category.objects.order_by("name")
        name = request.query_params.get("name", "").strip()
        if name:
            categories = categories.filter(title__icontains=name)
        serializer = CategorySerializer(
            categories, many=True, context={"request": request},
        )
        return Response(serializer.data)