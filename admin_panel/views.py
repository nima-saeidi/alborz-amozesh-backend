from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .serializers import AdminLoginSerializer, AdminRegisterSerializer, GallerySerializer
from django.contrib.auth import get_user_model
from .permissions import IsSuperAdmin
from .models import Gallery, AdminProfile

User = get_user_model()

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
