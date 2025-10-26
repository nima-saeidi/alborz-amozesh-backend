from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .serializers import (
    BaseRegisterSerializer,
    TeacherRegisterSerializer,
    LoginSerializer,
    TeacherUpdateProfileSerializer,
    StudentUpdateProfileSerializer
)
from .models import User, Teacher

# -------------------- Register API (Student) --------------------
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = BaseRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)


# -------------------- Register API (Teacher) --------------------
class TeacherRegisterAPIView(generics.CreateAPIView):
    serializer_class = TeacherRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT token
        refresh = RefreshToken.for_user(user)
        return Response({
            "user_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)


# -------------------- Login API --------------------
class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Update last login
            user.last_login = timezone.now()
            user.save()

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            return Response({
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# -------------------- Update Profile API --------------------
class UpdateProfileAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        user = self.request.user
        if hasattr(user, 'teacher'):  #to recegniz the user role by matching it to the databese relation
            return TeacherUpdateProfileSerializer
        else:
            return StudentUpdateProfileSerializer

    def get_object(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return user.teacher
        return user

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)