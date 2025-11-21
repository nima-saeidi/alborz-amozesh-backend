from rest_framework import generics, status, permissions, viewsets
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .serializers import AdminLoginSerializer, AdminRegisterSerializer, GallerySerializer, AdminCourseSerializer
from users.serializers import CourseSerializer, UserSerializer, Course
from django.contrib.auth import get_user_model
from .permissions import IsSuperAdmin, HasAdminLevel
from .models import Gallery, AdminProfile
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminLoginAPIView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)

        if user is not None and hasattr(user, 'admin_profile'):
            #update last login
            user.last_login = timezone.now()
            user.save()

            #create JWT
            refresh = RefreshToken.for_user(user)
            return Response({
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "access_level": user.admin_profile.access_level,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials or not an admin"}, status=status.HTTP_401_UNAUTHORIZED)




class AdminRegisterAPIView(generics.CreateAPIView):
    serializer_class = AdminRegisterSerializer
    permission_classes = [IsSuperAdmin]#if it is SuperAdmin

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "access_level": user.admin_profile.access_level,
            "access_level_name": user.admin_profile.get_access_level_display()
        }, status=status.HTTP_201_CREATED)


# ---------------------- Gallery (CRUD) ----------------------
class GalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [HasAdminLevel.level(1)]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

# ---------------------- Course (CRUD) ----------------------
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = AdminCourseSerializer
    permission_classes = [HasAdminLevel.level(4)]
    
        
# ---------------------- User (CRUD) ----------------------
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(5)] #superadmin