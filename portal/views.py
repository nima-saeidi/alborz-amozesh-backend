"""
Student panel API (all under /api/me/ need a JWT) + public certificate check, contact form and newsletter.
"""
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.access import can_access_session_files
from users.models import Course, CourseSession
from .models import Certificate, Favorite, NewsletterSubscriber, Notification, SessionProgress, Ticket, TicketMessage
from .serializers import (
    CertificateSerializer,
    ContactSerializer,
    NewsletterSerializer,
    NotificationSerializer,
    TeacherApplicationSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketReplySerializer,
    TicketSerializer,
    check_attachment,
)


def course_progress(user, course):
    """(watched sessions, all sessions) of a course for a user"""
    total = course.sessions.count()
    done = SessionProgress.objects.filter(user=user, session__course=course).count()
    return done, total


def progress_payload(user, course):
    done, total = course_progress(user, course)
    ids = list(SessionProgress.objects.filter(user=user, session__course=course).values_list('session_id', flat=True))
    return {'course': course.id, 'sessions': ids, 'done': done, 'total': total, 'percent': round(done / total * 100) if total else 0}


# -------------------- FAVORITES --------------------
class FavoriteListAPIView(APIView):
    """GET: favorite course ids. POST {course} or {courses: [...]} adds (used to merge the guest list at login)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(list(Favorite.objects.filter(user=request.user).values_list('course_id', flat=True)))

    def post(self, request):
        ids = request.data.get('courses') or [request.data.get('course')]
        try:
            ids = {int(i) for i in ids if i is not None}
        except (TypeError, ValueError):
            return Response({'course': 'شناسه دوره نامعتبر است.'}, status=status.HTTP_400_BAD_REQUEST)
        for course in Course.objects.filter(id__in=ids, is_active=True):
            Favorite.objects.get_or_create(user=request.user, course=course)
        return self.get(request)


class FavoriteDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, course_id):
        Favorite.objects.filter(user=request.user, course_id=course_id).delete()
        return Response(list(Favorite.objects.filter(user=request.user).values_list('course_id', flat=True)))


# -------------------- PROGRESS --------------------
class ProgressListAPIView(APIView):
    """{course_id: [watched session ids]} for every course the user has progress in"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = {}
        for course_id, session_id in SessionProgress.objects.filter(user=request.user).values_list('session__course_id', 'session_id'):
            result.setdefault(str(course_id), []).append(session_id)
        return Response(result)


class CourseProgressAPIView(APIView):
    """GET progress of one course, POST {session, done} marks / unmarks a session"""
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        return Response(progress_payload(request.user, get_object_or_404(Course, id=course_id)))

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        session = get_object_or_404(CourseSession, id=request.data.get('session'), course=course)
        if not can_access_session_files(request.user, session):
            return Response({'detail': 'برای این جلسه دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        if request.data.get('done', True) in (False, 'false', '0', 0):
            SessionProgress.objects.filter(user=request.user, session=session).delete()
        else:
            SessionProgress.objects.get_or_create(user=request.user, session=session)
        return Response(progress_payload(request.user, course))


# -------------------- CERTIFICATES --------------------
class CertificateListAPIView(APIView):
    """
    GET: issued certificates + the user's paid courses with their progress.
    POST {course}: issues the certificate when every session is watched.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        certificates = Certificate.objects.filter(user=request.user, is_revoked=False).select_related('course__teacher__user')
        issued = {c.course_id: c.code for c in certificates}
        courses = Course.objects.filter(invoices__student=request.user, invoices__paid=True).distinct().order_by('-invoices__date_time')
        progress = []
        for course in courses:
            done, total = course_progress(request.user, course)
            progress.append({
                'course': course.id, 'title': course.title, 'kind': course.kind, 'done': done, 'total': total,
                'percent': round(done / total * 100) if total else 0, 'certificate': issued.get(course.id),
            })
        return Response({'certificates': CertificateSerializer(certificates, many=True).data, 'courses': progress})

    def post(self, request):
        course = get_object_or_404(Course, id=request.data.get('course'))
        existing = Certificate.objects.filter(user=request.user, course=course).first()
        if existing:
            if existing.is_revoked:
                return Response({'detail': 'گواهی این دوره باطل شده است؛ با پشتیبانی تماس بگیرید.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(CertificateSerializer(existing).data)
        if not course.invoices.filter(student=request.user, paid=True).exists():
            return Response({'detail': 'ابتدا باید در این دوره ثبت‌نام کرده باشید.'}, status=status.HTTP_403_FORBIDDEN)
        done, total = course_progress(request.user, course)
        if not total or done < total:
            return Response({'detail': f'برای دریافت گواهی همه جلسات را کامل کنید ({done} از {total}).'}, status=status.HTTP_400_BAD_REQUEST)
        invoice = course.invoices.filter(student=request.user, paid=True).first()
        grade = invoice.grade or (f'{invoice.score:g}' if invoice.score is not None else '')
        certificate = Certificate.objects.create(user=request.user, course=course, grade=grade)
        return Response(CertificateSerializer(certificate).data, status=status.HTTP_201_CREATED)


class CertificateVerifyAPIView(APIView):
    """Public: anyone can check a certificate code"""
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def get(self, request, code):
        certificate = Certificate.objects.select_related('course__teacher__user').filter(code__iexact=code.strip()).first()
        if certificate is None or certificate.is_revoked:
            return Response({'valid': False, 'detail': 'گواهی‌نامه‌ای با این کد پیدا نشد.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'valid': True, **CertificateSerializer(certificate).data})


# -------------------- TICKETS --------------------
class TicketListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'tickets'

    def get_throttles(self):
        return super().get_throttles() if self.request.method == 'POST' else []

    def get(self, request):
        tickets = Ticket.objects.filter(user=request.user).select_related('course').prefetch_related('messages')
        return Response(TicketSerializer(tickets, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = TicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        attachment = check_attachment(data.get('attachment'))
        ticket = Ticket.objects.create(user=request.user, subject=data['subject'].strip(), department=data['department'], course=data.get('course'))
        TicketMessage.objects.create(ticket=ticket, author=request.user, text=data['text'], attachment=attachment)
        ticket.refresh_from_db()
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


class TicketDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        return Response(TicketDetailSerializer(get_object_or_404(Ticket, id=ticket_id, user=request.user)).data)


class TicketReplyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'tickets'

    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        if ticket.status == Ticket.Status.CLOSED:
            return Response({'detail': 'این تیکت بسته شده است؛ تیکت جدید ثبت کنید.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = check_attachment(serializer.validated_data.get('attachment'))
        TicketMessage.objects.create(ticket=ticket, author=request.user, text=serializer.validated_data['text'], attachment=attachment)
        ticket.refresh_from_db()
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


class TicketCloseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        ticket.status = Ticket.Status.CLOSED
        ticket.save(update_fields=['status', 'updated_at'])
        return Response(TicketDetailSerializer(ticket).data)


# -------------------- NOTIFICATIONS --------------------
def user_notifications(user):
    """The user's own notifications + announcements sent after they joined"""
    return (
        Notification.objects.filter(Q(user=user) | Q(user__isnull=True, created_at__gte=user.date_joined))
        .annotate(is_read=Exists(Notification.read_by.through.objects.filter(notification_id=OuterRef('pk'), user_id=user.id)))
    )


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = user_notifications(request.user)
        return Response({
            'unread': queryset.filter(is_read=False).count(),
            'results': NotificationSerializer(queryset[:50], many=True).data,
        })


class NotificationReadAPIView(APIView):
    """POST {ids: [...]} marks those as read; without ids marks everything"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        queryset = user_notifications(request.user).filter(is_read=False)
        ids = request.data.get('ids')
        if ids:
            queryset = queryset.filter(id__in=ids)
        for notification in queryset:
            notification.read_by.add(request.user)
        return Response({'unread': user_notifications(request.user).filter(is_read=False).count()})


# -------------------- TEACHER APPLICATION --------------------
class TeacherApplicationAPIView(APIView):
    """GET status of the logged in user's teacher profile, POST applies to teach (waits for admin approval)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = getattr(request.user, 'teacher', None)
        if teacher is None:
            return Response({'status': 'none'})
        return Response({'status': 'approved' if teacher.is_approved else 'pending', **TeacherApplicationSerializer(teacher).data})

    def post(self, request):
        if hasattr(request.user, 'teacher'):
            return Response({'detail': 'درخواست تدریس شما قبلاً ثبت شده است.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = TeacherApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, is_approved=False)
        return Response({'status': 'pending', **serializer.data}, status=status.HTTP_201_CREATED)


class TeacherStatsAPIView(APIView):
    """Numbers for the teacher's dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = getattr(request.user, 'teacher', None)
        if teacher is None or not teacher.is_approved:
            return Response({'detail': 'این بخش فقط برای اساتید تایید شده است.'}, status=status.HTTP_403_FORBIDDEN)
        courses = teacher.courses.annotate(students=Count('invoices', filter=Q(invoices__paid=True)))
        return Response({
            'courses': courses.count(),
            'active_courses': courses.filter(is_active=True).count(),
            'students': sum(c.students for c in courses),
            'sessions': CourseSession.objects.filter(course__teacher=teacher).count(),
        })


# -------------------- PUBLIC FORMS --------------------
class ContactAPIView(generics.CreateAPIView):
    serializer_class = ContactSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'contact'

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response({'detail': 'پیام شما ثبت شد؛ به‌زودی با شما تماس می‌گیریم.'}, status=status.HTTP_201_CREATED)


class NewsletterAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'contact'

    def post(self, request):
        serializer = NewsletterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber, created = NewsletterSubscriber.objects.get_or_create(phone_number=serializer.validated_data['phone_number'])
        if not created and not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=['is_active'])
        return Response({'detail': 'عضویت شما در خبرنامه پیامکی ثبت شد.'}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
