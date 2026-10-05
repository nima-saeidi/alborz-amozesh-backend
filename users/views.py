import mimetypes

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import Q, Count
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from admin_panel.models import Banner, Gallery, Partner, Comment
from admin_panel.serializers import BannerSerializer, PublicGallerySerializer, PartnerSerializer, PublicCommentSerializer
from .access import can_access_course_files, read_session_file_token, SESSION_FILE_KINDS
from .models import Teacher, Course, CourseSession, Invoice
from .pagination import StandardResultsSetPagination
from .serializers import (
    RegisterSerializer,
    TeacherRegisterSerializer,
    LoginSerializer,
    LogoutSerializer,
    UpdateCredentialsSerializer,
    UserProfileSerializer,
    ProfileUpdateSerializer,
    CourseListSerializer,
    CourseDetailSerializer,
    CourseSessionSerializer,
    TeacherCourseSerializer,
    TeacherSessionSerializer,
    TeacherPublicSerializer,
    InvoiceSerializer,
    EnrollSerializer,
)

User = get_user_model()


# -------------------- PERMISSIONS --------------------
class IsTeacher(BasePermission):
    """Approved teachers only"""
    message = 'این بخش فقط برای اساتید تایید شده است.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and hasattr(user, 'teacher') and user.teacher.is_approved)


# -------------------- HELPERS --------------------
def generate_jwt_response(user):
    refresh = RefreshToken.for_user(user)
    teacher = getattr(user, 'teacher', None)
    return {
        'user_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'is_teacher': teacher is not None,
        'teacher_approved': bool(teacher and teacher.is_approved),
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def public_courses():
    return (
        Course.objects.filter(is_active=True)
        .select_related('teacher__user')
        .annotate(
            total_students=Count('invoices', filter=Q(invoices__paid=True), distinct=True),
            sessions_count=Count('sessions', distinct=True),
        )
    )


# -------------------- AUTH --------------------
class RegisterAPIView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(generate_jwt_response(user), status=status.HTTP_201_CREATED)


class TeacherRegisterAPIView(generics.GenericAPIView):
    serializer_class = TeacherRegisterSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()
        data = generate_jwt_response(teacher.user)
        data['detail'] = 'ثبت‌نام انجام شد. پس از تایید مدیر می‌توانید دوره ایجاد کنید.'
        return Response(data, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].strip()
        password = serializer.validated_data['password']

        user = User.objects.filter(email__iexact=email).first()
        if user is None or not user.is_active or not user.check_password(password):
            return Response({'detail': 'ایمیل یا رمز عبور اشتباه است.'}, status=status.HTTP_401_UNAUTHORIZED)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        return Response(generate_jwt_response(user), status=status.HTTP_200_OK)


class LogoutAPIView(generics.GenericAPIView):
    """Blacklist the refresh token"""
    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            return Response({'detail': 'توکن نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'خروج انجام شد.'}, status=status.HTTP_200_OK)


# -------------------- PROFILE --------------------
class UserProfileAPIView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UpdateProfileInfoAPIView(generics.UpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        return Response({
            'detail': 'اطلاعات پروفایل به‌روزرسانی شد.',
            'updated_data': response.data,
        }, status=status.HTTP_200_OK)


class UpdateCredentialsAPIView(generics.GenericAPIView):
    serializer_class = UpdateCredentialsSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if serializer.validated_data.get('new_password'):
            user.set_password(serializer.validated_data['new_password'])
        if serializer.validated_data.get('email'):
            user.email = serializer.validated_data['email']
            user.username = serializer.validated_data['email']
        user.save()

        return Response({'detail': 'اطلاعات ورود به‌روزرسانی شد.'}, status=status.HTTP_200_OK)

    patch = put


# -------------------- COURSES (public) --------------------
class ListCoursesAPIView(generics.ListAPIView):
    """
    Filters: search, category, level, teacher (id)
    ordering: newest (default), oldest, price, -price, popular
    """
    serializer_class = CourseListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    ORDERINGS = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price': 'cost',
        '-price': '-cost',
        'popular': '-total_students',
    }

    def get_queryset(self):
        queryset = public_courses()
        params = self.request.query_params

        search = params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(short_description__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search) |
                Q(teacher__user__first_name__icontains=search) |
                Q(teacher__user__last_name__icontains=search)
            )
        if params.get('category'):
            queryset = queryset.filter(category__iexact=params['category'])
        if params.get('level'):
            queryset = queryset.filter(level__iexact=params['level'])
        if params.get('teacher'):
            queryset = queryset.filter(teacher_id=params['teacher'])

        ordering = self.ORDERINGS.get(params.get('ordering'), '-created_at')
        return queryset.order_by(ordering, '-id')


class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return public_courses().prefetch_related('sessions')


class CourseSessionListAPIView(generics.ListAPIView):
    """Sessions of an active course. File links only for enrolled (paid) students, the teacher and admins"""
    serializer_class = CourseSessionSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_course(self):
        if not hasattr(self, '_course'):
            self._course = get_object_or_404(Course, id=self.kwargs['course_id'], is_active=True)
        return self._course

    def get_queryset(self):
        return CourseSession.objects.filter(course=self.get_course()).order_by('order', 'id')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['course_access'] = can_access_course_files(self.request.user, self.get_course())
        return context


class CourseCategoriesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = (
            Course.objects.filter(is_active=True).exclude(category__isnull=True).exclude(category='')
            .values('category').annotate(count=Count('id')).order_by('category')
        )
        return Response([{'name': item['category'], 'count': item['count']} for item in categories])


# -------------------- TEACHERS (public) --------------------
class TeacherListAPIView(generics.ListAPIView):
    serializer_class = TeacherPublicSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return (
            Teacher.objects.filter(is_approved=True, user__is_active=True)
            .select_related('user')
            .annotate(courses_count=Count('courses', filter=Q(courses__is_active=True)))
            .order_by('user__last_name', 'id')
        )


class TeacherDetailAPIView(generics.RetrieveAPIView):
    serializer_class = TeacherPublicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        return TeacherListAPIView.get_queryset(self)


# -------------------- SITE CONTENT (public) --------------------
class PublicBannerListAPIView(generics.ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # start_date / end_date are optional: an empty date means no limit
        now = timezone.now()
        return Banner.objects.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now),
            is_active=True
        ).order_by('priority')


class PublicPartnerListAPIView(generics.ListAPIView):
    serializer_class = PartnerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Partner.objects.filter(is_active=True).order_by('priority', '-created_at')


class PublicGalleryListAPIView(generics.ListAPIView):
    serializer_class = PublicGallerySerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Gallery.objects.filter(is_published=True)


class CommentListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: approved comments (?course=<id> or ?user=<id>)
    POST: logged in users; a course comment requires a paid enrollment. Waits for admin approval
    """
    serializer_class = PublicCommentSerializer
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Comment.objects.filter(status=Comment.Status.APPROVED).select_related('author', 'course')
        if self.request.query_params.get('course'):
            queryset = queryset.filter(course_id=self.request.query_params['course'])
        if self.request.query_params.get('user'):
            queryset = queryset.filter(student_id=self.request.query_params['user'])
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, status=Comment.Status.PENDING)


# -------------------- STUDENT --------------------
class EnrollCourseAPIView(generics.GenericAPIView):
    """Creates the invoice. Free courses are paid immediately, others wait for the payment"""
    serializer_class = EnrollSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = Course.objects.select_for_update().filter(id=serializer.validated_data['course_id'], is_active=True).first()
        if course is None:
            return Response({'detail': 'دوره پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)
        if hasattr(request.user, 'teacher') and course.teacher_id == request.user.teacher.id:
            return Response({'detail': 'استاد نمی‌تواند در دوره خودش ثبت‌نام کند.'}, status=status.HTTP_400_BAD_REQUEST)
        if Invoice.objects.filter(student=request.user, course=course).exists():
            return Response({'detail': 'قبلاً در این دوره ثبت‌نام کرده‌اید.'}, status=status.HTTP_400_BAD_REQUEST)
        if course.limit_students is not None and course.invoices.filter(paid=True).count() >= course.limit_students:
            return Response({'detail': 'ظرفیت دوره تکمیل است.'}, status=status.HTTP_400_BAD_REQUEST)

        price = course.final_price
        free = not price
        invoice = Invoice.objects.create(
            student=request.user,
            course=course,
            amount=price,
            paid=free,
            paid_at=timezone.now() if free else None,
        )
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class RemoveCourseAPIView(generics.GenericAPIView):
    """Cancel an unpaid enrollment (course_id in the body or ?course_id=)"""
    serializer_class = EnrollSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        course_id = request.data.get('course_id') or request.query_params.get('course_id')
        invoice = get_object_or_404(Invoice, student=request.user, course_id=course_id)
        if invoice.paid:
            return Response({'detail': 'ثبت‌نام پرداخت‌شده قابل لغو نیست. با پشتیبانی تماس بگیرید.'}, status=status.HTTP_400_BAD_REQUEST)
        invoice.delete()
        return Response({'detail': 'ثبت‌نام لغو شد.'}, status=status.HTTP_200_OK)


class StudentInvoiceListAPIView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Invoice.objects.filter(student=self.request.user).select_related('course', 'student').order_by('-date_time')


class StudentCoursesAPIView(generics.ListAPIView):
    """Paid courses of the student (with access to the sessions)"""
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return public_courses().filter(invoices__student=self.request.user, invoices__paid=True).order_by('-created_at')


# -------------------- TEACHER --------------------
class TeacherCourseMixin:
    serializer_class = TeacherCourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Course.objects.filter(teacher__user=self.request.user).prefetch_related('sessions').order_by('-created_at')

    def get_object(self):
        return get_object_or_404(self.get_queryset(), id=self.kwargs.get('course_id'))


class TeacherCoursesListAPIView(TeacherCourseMixin, generics.ListAPIView):
    pass


class TeacherCourseCreateAPIView(TeacherCourseMixin, generics.CreateAPIView):
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher)


class TeacherCourseDetailAPIView(TeacherCourseMixin, generics.RetrieveAPIView):
    pass


class TeacherCourseUpdateAPIView(TeacherCourseMixin, generics.UpdateAPIView):
    pass


class TeacherCourseDeleteAPIView(TeacherCourseMixin, generics.DestroyAPIView):
    def destroy(self, request, *args, **kwargs):
        course = self.get_object()
        if course.invoices.filter(paid=True).exists():
            return Response({'detail': 'این دوره دانشجوی پرداخت‌کرده دارد و قابل حذف نیست؛ آن را غیرفعال کنید.'}, status=status.HTTP_400_BAD_REQUEST)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherCourseStudentsAPIView(TeacherCourseMixin, generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        course = self.get_object()
        invoices = course.invoices.select_related('student').order_by('-date_time')
        return Response({
            'course_title': course.title,
            'total_students': invoices.filter(paid=True).count(),
            'students': [
                {
                    'id': invoice.student.id,
                    'name': invoice.student.get_full_name(),
                    'email': invoice.student.email,
                    'paid': invoice.paid,
                    'grade': invoice.grade,
                    'score': invoice.score,
                    'date_time': invoice.date_time,
                }
                for invoice in invoices
            ],
            'sessions': CourseSessionSerializer(course.sessions.all(), many=True, context={'request': request, 'course_access': True}).data,
        }, status=status.HTTP_200_OK)


class TeacherSessionListCreateAPIView(generics.ListCreateAPIView):
    """Sessions of one of the teacher's courses (upload video / pdf with multipart)"""
    serializer_class = TeacherSessionSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_course(self):
        return get_object_or_404(Course, id=self.kwargs['course_id'], teacher__user=self.request.user)

    def get_queryset(self):
        return self.get_course().sessions.all()

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'course_access': True}

    def perform_create(self, serializer):
        serializer.save(course=self.get_course())


class TeacherSessionDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TeacherSessionSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_url_kwarg = 'session_id'

    def get_queryset(self):
        return CourseSession.objects.filter(course__teacher__user=self.request.user)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'course_access': True}


# -------------------- PROTECTED SESSION FILES --------------------
class SessionFileAPIView(APIView):
    """
    Downloads / streams a session file from a signed link (given in the session serializers).
    In production nginx sends the file (X-Accel-Redirect)
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, session_id, kind):
        if kind not in SESSION_FILE_KINDS:
            raise Http404
        try:
            read_session_file_token(request.query_params.get('token', ''), session_id, kind)
        except signing.SignatureExpired:
            return Response({'detail': 'لینک منقضی شده است.'}, status=status.HTTP_403_FORBIDDEN)
        except signing.BadSignature:
            return Response({'detail': 'لینک نامعتبر است.'}, status=status.HTTP_403_FORBIDDEN)

        session = get_object_or_404(CourseSession, id=session_id)
        file = getattr(session, kind)
        if not file:
            raise Http404

        content_type = mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
        if settings.PROTECTED_MEDIA_USE_ACCEL:
            response = HttpResponse(content_type=content_type)
            response['X-Accel-Redirect'] = settings.PROTECTED_MEDIA_ACCEL_PREFIX + file.name
            return response

        return FileResponse(file.open('rb'), content_type=content_type)
