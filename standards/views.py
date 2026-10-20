from django.db.models import Count, F, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import generics, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from admin_panel.permissions import HasAdminLevel
from users.pagination import StandardResultsSetPagination
from .models import StandardCategory, TechnicalStandard
from .serializers import AdminTechnicalStandardSerializer, StandardCategorySerializer, TechnicalStandardSerializer


def published_standards():
    return TechnicalStandard.objects.filter(is_published=True).select_related('category')


# -------------------- PUBLIC --------------------
class StandardListAPIView(generics.ListAPIView):
    """Filters: search (title, code, description), category (id)"""
    serializer_class = TechnicalStandardSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = published_standards()
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(code__icontains=search) | Q(description__icontains=search))
        category = self.request.query_params.get('category')
        if category and category.isdigit():
            queryset = queryset.filter(category_id=int(category))
        return queryset


class StandardCategoryListAPIView(generics.ListAPIView):
    serializer_class = StandardCategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return StandardCategory.objects.annotate(
            standards_count=Count('standards', filter=Q(standards__is_published=True))
        ).filter(standards_count__gt=0)


class StandardDetailAPIView(generics.RetrieveAPIView):
    serializer_class = TechnicalStandardSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return published_standards()


class StandardFileAPIView(APIView):
    """Counts the download and redirects to the PDF"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, id):
        standard = get_object_or_404(published_standards(), id=id)
        TechnicalStandard.objects.filter(pk=standard.pk).update(downloads=F('downloads') + 1)
        return HttpResponseRedirect(standard.pdf.url)


# -------------------- ADMIN API (/api/admin/) --------------------
class AdminStandardViewSet(viewsets.ModelViewSet):
    queryset = TechnicalStandard.objects.select_related('category')
    serializer_class = AdminTechnicalStandardSerializer
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardResultsSetPagination


class AdminStandardCategoryViewSet(viewsets.ModelViewSet):
    queryset = StandardCategory.objects.annotate(standards_count=Count('standards'))
    serializer_class = StandardCategorySerializer
    permission_classes = [HasAdminLevel.level(4)]
    pagination_class = None
