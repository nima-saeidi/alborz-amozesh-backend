# ===========================================
# users/views.py — Final Optimized Version
# ===========================================

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db import transaction
from .serializers import (
    BaseRegisterSerializer,
    TeacherRegisterSerializer,
    LoginSerializer,
    TeacherUpdateProfileSerializer,
    StudentUpdateProfileSerializer,
    CourseSerializer,
    TeacherSerializer,
    UserProfileSerializer,
)
from .models import User, Teacher, Course, Invoice
from django.shortcuts import get_object_or_404


# ====================================================
# Helper Function to Generate JWT Response
# ====================================================
def generate_jwt_response(user):
    """Generate JWT tokens for a given user and return a standard response."""
    refresh = RefreshToken.for_user(user)
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "refresh": str(refresh),
        "access": str(refresh.access_token)
    }


# ====================================================
# Register API (Student)
# ====================================================
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = BaseRegisterSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return Response(generate_jwt_response(user), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": f"Registration error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# ====================================================
# Register API (Teacher)
# ====================================================
class TeacherRegisterAPIView(generics.CreateAPIView):
    serializer_class = TeacherRegisterSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            return Response(generate_jwt_response(user), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": f"Teacher registration error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# ====================================================
# Login API
# ====================================================
class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, username=email, password=password)

            if user is None:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            # Update last login time
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            return Response(generate_jwt_response(user), status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": f"Login error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


# ====================================================
# Update Profile API
# ====================================================
class UpdateProfileAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return TeacherUpdateProfileSerializer
        return StudentUpdateProfileSerializer

    def get_object(self):
        user = self.request.user
        return user.teacher if hasattr(user, 'teacher') else user

    def put(self, request, *args, **kwargs):
        """
        Update profile info. After successful update, remove current_password from response.
        """
        response = super().update(request, *args, **kwargs)
        if isinstance(response.data, dict) and 'current_password' in response.data:
            response.data.pop('current_password', None)
        return Response({
            "detail": "Profile updated successfully",
            "updated_data": response.data
        }, status=status.HTTP_200_OK)



# -------------------- 1️⃣ انتخاب دوره توسط یوزر (تست) --------------------
class SelectCourseAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            course_id = request.data.get('course_id')
            course = get_object_or_404(Course, id=course_id)

            # بررسی اکتیو بودن دوره
            if not course.is_active:
                return Response({"detail": "Course is not active."}, status=status.HTTP_400_BAD_REQUEST)

            # بررسی محدودیت دانشجو
            current_students = Invoice.objects.filter(course=course).count()
            if course.limit_students and current_students >= course.limit_students:
                return Response({"detail": "Course student limit reached."}, status=status.HTTP_400_BAD_REQUEST)

            # ثبت دوره برای کاربر (Invoice)
            invoice = Invoice.objects.create(student=request.user, course=course, paid=False)
            return Response({"detail": f"Course '{course.title}' selected successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------- 2️⃣ حذف دوره توسط یوزر (تست) --------------------
class RemoveCourseAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        try:
            course_id = request.data.get('course_id')
            invoice = get_object_or_404(Invoice, student=request.user, course_id=course_id)
            invoice.delete()
            return Response({"detail": "Course removed successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------- 3️⃣ نمایش تمام دوره‌ها --------------------
class ListCoursesAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CourseSerializer
    queryset = Course.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------- 4️⃣ نمایش تمام مدرس‌ها --------------------
class ListTeachersAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = TeacherSerializer
    queryset = Teacher.objects.all()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# -------------------- 5️⃣ پروفایل کاربر و دوره‌های انتخاب شده --------------------
class UserProfileAPIView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)