from rest_framework import serializers

from users.models import Course, Teacher
from users.phone import normalize_phone
from .models import Certificate, ContactMessage, Notification, Ticket, TicketMessage


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_kind = serializers.CharField(source='course.kind', read_only=True)
    course_duration = serializers.IntegerField(source='course.duration', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = ['id', 'code', 'course', 'course_title', 'course_kind', 'course_duration', 'teacher_name', 'full_name', 'grade', 'issued_at']

    def get_teacher_name(self, obj):
        return obj.course.teacher.user.get_full_name()


class TicketMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = ['id', 'text', 'is_staff_reply', 'author_name', 'attachment', 'created_at']

    def get_author_name(self, obj):
        if obj.is_staff_reply:
            return 'پشتیبانی البرز'
        return obj.author.get_full_name() if obj.author else ''


class TicketSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'department', 'course', 'course_title', 'status', 'created_at', 'updated_at', 'last_message']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        message = obj.messages.last()
        return message.text[:120] if message else ''


class TicketDetailSerializer(TicketSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ['messages']


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    department = serializers.ChoiceField(choices=Ticket.Department.choices, default=Ticket.Department.EDUCATION)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), required=False, allow_null=True)
    text = serializers.CharField(max_length=5000)
    attachment = serializers.FileField(required=False, allow_null=True)

    def validate_text(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError('متن پیام خیلی کوتاه است.')
        return value.strip()


class TicketReplySerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000)
    attachment = serializers.FileField(required=False, allow_null=True)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError('متن پیام را بنویسید.')
        return value.strip()


ATTACHMENT_MAX_BYTES = 5 * 1024 * 1024
ATTACHMENT_TYPES = ('.pdf', '.jpg', '.jpeg', '.png', '.webp', '.zip', '.txt', '.docx')


def check_attachment(file):
    if not file:
        return None
    if file.size > ATTACHMENT_MAX_BYTES:
        raise serializers.ValidationError({'attachment': 'حجم پیوست باید کمتر از ۵ مگابایت باشد.'})
    if not file.name.lower().endswith(ATTACHMENT_TYPES):
        raise serializers.ValidationError({'attachment': 'نوع فایل مجاز نیست (PDF، تصویر، ZIP، TXT یا DOCX).'})
    return file


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'title', 'text', 'link', 'created_at', 'is_read']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['name', 'phone', 'email', 'subject', 'message']

    def validate(self, attrs):
        if not attrs.get('phone') and not attrs.get('email'):
            raise serializers.ValidationError({'phone': 'شماره تماس یا ایمیل را وارد کنید.'})
        if len(attrs['message'].strip()) < 10:
            raise serializers.ValidationError({'message': 'پیام خیلی کوتاه است.'})
        return attrs


class NewsletterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        phone = normalize_phone(value)
        if phone is None:
            raise serializers.ValidationError('شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷).')
        return phone


class TeacherApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['education_degree', 'academic_field', 'bio', 'is_approved']
        read_only_fields = ['is_approved']
