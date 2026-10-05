from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Course, CourseSession, Invoice, Teacher
from users.pagination import StandardResultsSetPagination
from .models import AdminProfile, Banner, Gallery, Comment, Partner
from .permissions import IsSuperAdmin, HasAdminLevel, admin_level
from .serializers import (
    AdminLoginSerializer,
    AdminRegisterSerializer,
    AdminUserSerializer,
    AdminTeacherSerializer,
    AdminCourseSerializer,
    AdminSessionSerializer,
    AdminInvoiceSerializer,
    BannerSerializer,
    GallerySerializer,
    CommentSerializer,
    PartnerSerializer,
)

User = get_user_model()

UPLOAD_PARSERS = [MultiPartParser, FormParser, JSONParser]


def bool_param(_value):
    if _value in ('true', '1'):
        return True
    if _value in ('false', '0'):
        return False
    return None


# -------------------- AUTH --------------------
class AdminLoginAPIView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data['email'].strip()).first()
        if user is None or not user.is_active or not user.check_password(serializer.validated_data['password']) or not hasattr(user, 'admin_profile'):
            return Response({'detail': 'ایمیل یا رمز عبور اشتباه است یا دسترسی ادمین ندارید.'}, status=status.HTTP_401_UNAUTHORIZED)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        return Response({
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'access_level': user.admin_profile.access_level,
            'access_level_name': user.admin_profile.get_access_level_display(),
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class AdminRegisterAPIView(generics.GenericAPIView):
    serializer_class = AdminRegisterSerializer
    permission_classes = [IsSuperAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'access_level': user.admin_profile.access_level,
            'access_level_name': user.admin_profile.get_access_level_display(),
        }, status=status.HTTP_201_CREATED)


class AdminMeAPIView(APIView):
    permission_classes = [HasAdminLevel.level(1)]

    def get(self, request):
        level = admin_level(request.user)
        return Response({
            'user_id': request.user.id,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'access_level': level,
            'access_level_name': dict(AdminProfile.ACCESS_LEVEL_CHOICES).get(level),
        })


# -------------------- DASHBOARD --------------------
class AdminDashboardAPIView(APIView):
    """Numbers for the admin home page"""
    permission_classes = [HasAdminLevel.level(4)]

    def get(self, request):
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        paid = Invoice.objects.filter(paid=True)

        top_courses = (
            Course.objects.annotate(students=Count('invoices', filter=Q(invoices__paid=True)))
            .order_by('-students')[:5]
        )

        return Response({
            'users': {
                'total': User.objects.count(),
                'new_last_30_days': User.objects.filter(date_joined__gte=month_ago).count(),
            },
            'teachers': {
                'total': Teacher.objects.count(),
                'pending_approval': Teacher.objects.filter(is_approved=False).count(),
            },
            'courses': {
                'total': Course.objects.count(),
                'active': Course.objects.filter(is_active=True).count(),
                'sessions': CourseSession.objects.count(),
            },
            'invoices': {
                'total': Invoice.objects.count(),
                'paid': paid.count(),
                'unpaid': Invoice.objects.filter(paid=False).count(),
                'revenue': paid.aggregate(total=Sum('amount'))['total'] or 0,
                'revenue_last_30_days': paid.filter(paid_at__gte=month_ago).aggregate(total=Sum('amount'))['total'] or 0,
            },
            'comments': {
                'pending': Comment.objects.filter(status=Comment.Status.PENDING).count(),
            },
            'top_courses': [{'id': course.id, 'title': course.title, 'students': course.students} for course in top_courses],
        })


# -------------------- USERS (super admin) --------------------
class AdminUserViewSet(viewsets.ModelViewSet):
    """?search= &is_teacher=true|false &is_active=true|false"""
    serializer_class = AdminUserSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(5)]
    parser_classes = UPLOAD_PARSERS
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = User.objects.select_related('teacher', 'admin_profile').annotate(invoices_count=Count('invoices')).order_by('-date_joined')
        params = self.request.query_params
        if params.get('search'):
            search = params['search']
            queryset = queryset.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search) |
                Q(email__icontains=search) | Q(phone_number__icontains=search) | Q(national_id__icontains=search)
            )
        is_teacher = bool_param(params.get('is_teacher'))
        if is_teacher is not None:
            queryset = queryset.filter(teacher__isnull=not is_teacher)
        is_active = bool_param(params.get('is_active'))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'نمی‌توانید حساب خودتان را حذف کنید.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


# -------------------- TEACHERS --------------------
class AdminTeacherViewSet(viewsets.ModelViewSet):
    """?approved=true|false &search="""
    serializer_class = AdminTeacherSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = UPLOAD_PARSERS
    http_method_names = ['get', 'put', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = Teacher.objects.select_related('user').annotate(courses_count=Count('courses')).order_by('is_approved', '-id')
        approved = bool_param(self.request.query_params.get('approved'))
        if approved is not None:
            queryset = queryset.filter(is_approved=approved)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search) | Q(user__email__icontains=search))
        return queryset

    def create(self, request, *args, **kwargs):
        return Response({'detail': 'اساتید از طریق ثبت‌نام استاد ساخته می‌شوند.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        teacher = self.get_object()
        teacher.is_approved = True
        teacher.save(update_fields=['is_approved'])
        return Response({'detail': 'استاد تایید شد.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        teacher = self.get_object()
        teacher.is_approved = False
        teacher.save(update_fields=['is_approved'])
        return Response({'detail': 'تایید استاد لغو شد.'})


# -------------------- COURSES / SESSIONS / INVOICES --------------------
class AdminCourseViewSet(viewsets.ModelViewSet):
    """?search= &teacher= &is_active=true|false"""
    serializer_class = AdminCourseSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = UPLOAD_PARSERS

    def get_queryset(self):
        queryset = Course.objects.select_related('teacher__user').annotate(
            total_students=Count('invoices', filter=Q(invoices__paid=True))
        ).order_by('-created_at')
        params = self.request.query_params
        if params.get('search'):
            queryset = queryset.filter(title__icontains=params['search'])
        if params.get('teacher'):
            queryset = queryset.filter(teacher_id=params['teacher'])
        is_active = bool_param(params.get('is_active'))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset


class AdminSessionViewSet(viewsets.ModelViewSet):
    """?course="""
    serializer_class = AdminSessionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = UPLOAD_PARSERS

    def get_queryset(self):
        queryset = CourseSession.objects.select_related('course').order_by('course_id', 'order', 'id')
        if self.request.query_params.get('course'):
            queryset = queryset.filter(course_id=self.request.query_params['course'])
        return queryset


class AdminInvoiceViewSet(viewsets.ModelViewSet):
    """?paid=true|false &course= &student= &search="""
    serializer_class = AdminInvoiceSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]

    def get_queryset(self):
        queryset = Invoice.objects.select_related('student', 'course').order_by('-date_time')
        params = self.request.query_params
        paid = bool_param(params.get('paid'))
        if paid is not None:
            queryset = queryset.filter(paid=paid)
        if params.get('course'):
            queryset = queryset.filter(course_id=params['course'])
        if params.get('student'):
            queryset = queryset.filter(student_id=params['student'])
        if params.get('search'):
            search = params['search']
            queryset = queryset.filter(Q(student__email__icontains=search) | Q(student__last_name__icontains=search) | Q(course__title__icontains=search))
        return queryset

    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        invoice = self.get_object()
        invoice.paid = True
        invoice.paid_at = invoice.paid_at or timezone.now()
        if invoice.amount is None:
            invoice.amount = invoice.course.final_price
        invoice.save(update_fields=['paid', 'paid_at', 'amount'])
        return Response(self.get_serializer(invoice).data)


# -------------------- GALLERY --------------------
class AdminGalleryViewSet(viewsets.ModelViewSet):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(1)]
    parser_classes = UPLOAD_PARSERS

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


# -------------------- COMMENTS --------------------
class AdminCommentViewSet(viewsets.ModelViewSet):
    """?status= &student= &author= &course="""
    serializer_class = CommentSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]

    def get_queryset(self):
        queryset = Comment.objects.select_related('student', 'author', 'course').order_by('-created_at')
        params = self.request.query_params
        if params.get('status'):
            queryset = queryset.filter(status=params['status'])
        if params.get('student'):
            queryset = queryset.filter(student_id=params['student'])
        if params.get('author'):
            queryset = queryset.filter(author_id=params['author'])
        if params.get('course'):
            queryset = queryset.filter(course_id=params['course'])
        return queryset

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        comment = self.get_object()
        comment.status = Comment.Status.APPROVED
        comment.save(update_fields=['status'])
        return Response(self.get_serializer(comment).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        comment = self.get_object()
        comment.status = Comment.Status.REJECTED
        comment.save(update_fields=['status'])
        return Response(self.get_serializer(comment).data)


# -------------------- BANNERS / PARTNERS --------------------
class AdminBannerViewSet(viewsets.ModelViewSet):
    """?active=true|false"""
    serializer_class = BannerSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = UPLOAD_PARSERS

    def get_queryset(self):
        queryset = Banner.objects.all().order_by('priority')
        active = bool_param(self.request.query_params.get('active'))
        if active is not None:
            queryset = queryset.filter(is_active=active)
        return queryset


class AdminPartnerViewSet(viewsets.ModelViewSet):
    """?is_active=true|false"""
    serializer_class = PartnerSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [HasAdminLevel.level(4)]
    parser_classes = UPLOAD_PARSERS

    def get_queryset(self):
        queryset = Partner.objects.all().order_by('priority', '-created_at')
        is_active = bool_param(self.request.query_params.get('is_active'))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset
