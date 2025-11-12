from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .serializers import AdminLoginSerializer, AdminRegisterSerializer, GallerySerializer
from users.serializers import CourseSerializer, UserSerializer
from django.contrib.auth import get_user_model
from .permissions import IsSuperAdmin
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



class GalleryCreateAPIView(generics.CreateAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        # if the user is admin
        if not hasattr(user, 'admin_profile'):
            return Response({"detail": "Only admins can access this API."}, status=status.HTTP_403_FORBIDDEN)

        admin_profile = user.admin_profile

        # access able just for admin level 1,5
        if admin_profile.access_level not in [1, 5]:
            return Response({"detail": "You do not have permission to add gallery items."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class CreateCourseAPIView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]  
    
    def post(self, request):
        user = request.user

        # check for if user is admin or not
        if not hasattr(user, 'admin_profile'):
            return Response({"error": "Only admins can access this API."}, status=status.HTTP_403_FORBIDDEN)

        admin_profile = user.admin_profile

        # access leve of admin
        if admin_profile.access_level >= 4:
            return Response({"error": "You do not have permission to add course."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "sucseesful", "course": serializer.data}, 
                            status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        # access leve of admin
        if hasattr(user, 'admin_profile') and user.admin_profile.access_level == 5:
            return User.objects.all().order_by('id')
        else:
            raise PermissionDenied("You do not have permission to view this resource.")
        
        
class AdminUserUpdateAPIView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = super().get_object()
        admin = self.request.user
        
        if hasattr(admin, 'admin_profile') and admin.admin_profile.access_level == 5:
            return user
        else:
            raise PermissionDenied("You do not have permission to edit this user.")