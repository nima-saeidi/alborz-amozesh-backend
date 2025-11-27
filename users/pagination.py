# ================================================
# users/pagination.py
# Global reusable pagination class
# ================================================

from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    A reusable pagination class that can be used in ANY ListAPIView.
    - Default page size: 10
    - Supports ?page_size= parameter
    - Prevents huge responses by limiting max page size to 100
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
