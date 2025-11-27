from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .pagination import StandardResultsSetPagination
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Teacher, Course, CourseSession, Invoice
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import (
    BaseRegisterSerializer,
    TeacherRegisterSerializer,
    LoginSerializer,
    TeacherUpdateProfileSerializer,
    StudentUpdateProfileSerializer,
    UserProfileSerializer,
    UpdateCredentialsSerializer,
    CourseSerializer,
    CourseSessionSerializer,
    InvoiceSerializer,
)

from rest_framework.permissions import BasePermission

# -------------------- PERMISSIONS --------------------
class IsTeacher(BasePermission):
    message = "This action is only allowed for teachers."
    def has_permission(self, request, view):
        return hasattr(request.user, 'teacher')

# -------------------- JWT HELPER --------------------
def generate_jwt_response(user):
    refresh = RefreshToken.for_user(user)
    is_teacher = hasattr(user, 'teacher')
    return {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_teacher": is_teacher,
        "refresh": str(refresh),
        "access": str(refresh.access_token)
    }

# -------------------- REGISTER --------------------
class RegisterAPIView(generics.CreateAPIView):
    serializer_class = BaseRegisterSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(generate_jwt_response(user), status=status.HTTP_201_CREATED)

class TeacherRegisterAPIView(generics.CreateAPIView):
    serializer_class = TeacherRegisterSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()
        return Response(generate_jwt_response(teacher.user), status=status.HTTP_201_CREATED)

# -------------------- LOGIN --------------------
class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        return Response(generate_jwt_response(user), status=status.HTTP_200_OK)

# -------------------- PROFILE --------------------
class UpdateCredentialsAPIView(generics.UpdateAPIView):
    serializer_class = UpdateCredentialsSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        current_password = serializer.validated_data.get("current_password")
        new_password = serializer.validated_data.get("new_password")
        new_email = serializer.validated_data.get("email")

        if not user.check_password(current_password):
            return Response({"detail": "Current password is incorrect."}, status=400)

        if new_password:
            validate_password(new_password, user)
            user.set_password(new_password)

        if new_email:
            user.email = new_email
            user.username = new_email

        user.save()
        return Response({"detail": "Credentials updated successfully."}, status=200)

class UpdateProfileInfoAPIView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def get_serializer_class(self):
        user = self.request.user
        if hasattr(user, 'teacher'):
            return TeacherUpdateProfileSerializer
        return StudentUpdateProfileSerializer

    def get_object(self):
        user = self.request.user
        return user.teacher if hasattr(user, 'teacher') else user

    def put(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            "detail": "Profile information updated successfully",
            "updated_data": response.data
        }, status=status.HTTP_200_OK)

class UserProfileAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

# -------------------- COURSES --------------------
class ListCoursesAPIView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True)
        search = self.request.query_params.get("search")
        category = self.request.query_params.get("category")
        level = self.request.query_params.get("level")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(teacher__user__first_name__icontains=search)
            )
        if category:
            queryset = queryset.filter(category__iexact=category)
        if level:
            queryset = queryset.filter(level__iexact=level)
        return queryset.order_by("-created_at")

class CourseDetailAPIView(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = "id"

class CourseSessionListAPIView(generics.ListAPIView):
    serializer_class = CourseSessionSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        return CourseSession.objects.filter(course_id=course_id).order_by("id")

# -------------------- STUDENT COURSE MANAGEMENT --------------------
class EnrollCourseAPIView(generics.CreateAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        course_id = request.data.get("course_id")
        if Invoice.objects.filter(student=request.user, course_id=course_id).exists():
            return Response({"detail": "Already enrolled"}, status=status.HTTP_400_BAD_REQUEST)
        invoice = Invoice.objects.create(student=request.user, course_id=course_id, paid=False)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

class RemoveCourseAPIView(generics.DestroyAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        course_id = request.data.get("course_id")
        invoice = get_object_or_404(Invoice, student=request.user, course_id=course_id)
        invoice.delete()
        return Response({"detail": "Course removed successfully"}, status=status.HTTP_200_OK)

class StudentInvoiceListAPIView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Invoice.objects.filter(student=self.request.user).order_by("-date_time")

# -------------------- TEACHER COURSE MANAGEMENT --------------------
class TeacherCoursesListAPIView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        return Course.objects.filter(teacher__user=self.request.user)

class TeacherCourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self):
        course_id = self.kwargs.get("course_id")
        return get_object_or_404(Course, id=course_id, teacher__user=self.request.user)

class TeacherCourseStudentsAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, *args, **kwargs):
        course_id = self.kwargs.get("course_id")
        course = get_object_or_404(Course, id=course_id, teacher__user=request.user)
        students = Invoice.objects.filter(course=course).select_related('student')
        data = {
            "course_title": course.title,
            "total_students": students.count(),
            "students": [{"id": s.student.id, "name": f"{s.student.first_name} {s.student.last_name}", "email": s.student.email} for s in students],
            "sessions": CourseSessionSerializer(course.sessions.all(), many=True).data
        }
        return Response(data, status=status.HTTP_200_OK)

class TeacherCourseCreateAPIView(generics.CreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher)

class TeacherCourseUpdateAPIView(generics.UpdateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self):
        course_id = self.kwargs.get("course_id")
        return get_object_or_404(Course, id=course_id, teacher__user=self.request.user)

class TeacherCourseDeleteAPIView(generics.DestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]

    def get_object(self):
        course_id = self.kwargs.get("course_id")
        return get_object_or_404(Course, id=course_id, teacher__user=self.request.user)

    def perform_destroy(self, instance):
        instance.sessions.all().delete()
        instance.delete()
