from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .serializers import AdminLoginSerializer, AdminRegisterSerializer
from django.contrib.auth import get_user_model
from .permissions import IsSuperAdmin
from rest_framework.permissions import AllowAny

User = get_user_model()

class AdminLoginAPIView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer
    permission_classes = [AllowAny]

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
