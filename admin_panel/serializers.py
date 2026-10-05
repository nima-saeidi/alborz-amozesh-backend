from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from users.models import User, Course, CourseSession, Invoice, Teacher
from users.serializers import validate_unique_email
from .models import AdminProfile, Gallery, Comment, Banner, Partner


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class AdminProfileSerializer(serializers.ModelSerializer):
    access_level_name = serializers.CharField(source='get_access_level_display', read_only=True)

    class Meta:
        model = AdminProfile
        fields = ('user', 'register_datetime', 'activity_history', 'access_level', 'access_level_name')


# -------------------- ADMIN REGISTRATION (super admin only) --------------------
class AdminRegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    access_level = serializers.ChoiceField(choices=AdminProfile.ACCESS_LEVEL_CHOICES)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password', 'access_level')

    def validate_email(self, value):
        return validate_unique_email(value)

    @transaction.atomic
    def create(self, validated_data):
        access_level = validated_data.pop('access_level')
        user = User(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            # Level 4+ admins can also use the Django admin site
            is_staff=access_level >= 4,
        )
        user.set_password(validated_data['password'])
        user.save()
        AdminProfile.objects.create(user=user, access_level=access_level)
        return user


# -------------------- USERS --------------------
class AdminUserSerializer(serializers.ModelSerializer):
    is_teacher = serializers.BooleanField(read_only=True)
    teacher_approved = serializers.SerializerMethodField()
    access_level = serializers.SerializerMethodField()
    invoices_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'birthday_date', 'national_id', 'gender',
            'fathers_name', 'education_level', 'profile_image', 'is_active', 'is_teacher', 'teacher_approved',
            'access_level', 'invoices_count', 'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']

    def get_teacher_approved(self, obj):
        return obj.teacher.is_approved if hasattr(obj, 'teacher') else None

    def get_access_level(self, obj):
        return obj.admin_profile.access_level if hasattr(obj, 'admin_profile') else None

    def validate_email(self, value):
        return validate_unique_email(value, _exclude_user=self.instance)

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            instance.username = validated_data['email']
        return super().update(instance, validated_data)


class AdminTeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    courses_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'full_name', 'email', 'phone_number', 'education_degree', 'academic_field', 'bio', 'profile_image', 'is_approved', 'courses_count']
        read_only_fields = ['user']


# -------------------- GALLERY --------------------
class GallerySerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField(read_only=True)
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = Gallery
        fields = '__all__'
        read_only_fields = ('id', 'uploaded_at', 'uploaded_by', 'views_count')

    def get_image_src(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return obj.image_url

    def validate(self, attrs):
        image = attrs.get('image', getattr(self.instance, 'image', None))
        image_url = attrs.get('image_url', getattr(self.instance, 'image_url', None))
        if not image and not image_url:
            raise serializers.ValidationError('یک تصویر آپلود کنید یا لینک تصویر را وارد کنید.')
        return attrs


class PublicGallerySerializer(GallerySerializer):
    class Meta:
        model = Gallery
        fields = ['id', 'title', 'description', 'image_src', 'event_date', 'tags']


# -------------------- COURSES / SESSIONS / INVOICES --------------------
class AdminCourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    total_students = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['rating_avg', 'created_at', 'last_updated']


class AdminSessionSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = CourseSession
        fields = ['id', 'course', 'course_title', 'title', 'description', 'order', 'is_free', 'video', 'pdf', 'created_at']
        read_only_fields = ['created_at']


class AdminInvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'student', 'student_name', 'student_email', 'course', 'course_title', 'amount', 'paid', 'paid_at', 'grade', 'score', 'date_time']
        read_only_fields = ['date_time']

    def validate_score(self, value):
        if value is not None and not 0 <= value <= 100:
            raise serializers.ValidationError('نمره باید بین ۰ تا ۱۰۰ باشد.')
        return value

    def save(self, **kwargs):
        # Keep paid_at in sync with paid
        paid = self.validated_data.get('paid')
        if paid is True and not (self.instance and self.instance.paid_at) and 'paid_at' not in self.validated_data:
            kwargs['paid_at'] = timezone.now()
        if paid is False:
            kwargs['paid_at'] = None
        if not self.instance and 'amount' not in self.validated_data:
            kwargs['amount'] = self.validated_data['course'].final_price
        return super().save(**kwargs)


# -------------------- COMMENTS --------------------
class CommentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True, default=None)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True, default=None)
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)

    class Meta:
        model = Comment
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 'author', 'author_name', 'text', 'rating', 'status', 'created_at']
        read_only_fields = ['created_at']


class PublicCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)

    class Meta:
        model = Comment
        fields = ['id', 'course', 'course_title', 'student', 'author_name', 'text', 'rating', 'status', 'created_at']
        read_only_fields = ['status', 'created_at']
        extra_kwargs = {'student': {'label': 'user'}}

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else 'کاربر'

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('امتیاز باید بین ۱ تا ۵ باشد.')
        return value

    def validate(self, attrs):
        course = attrs.get('course')
        if not course and not attrs.get('student'):
            raise serializers.ValidationError('دوره یا کاربر مورد نظر را مشخص کنید.')
        user = self.context['request'].user
        if course and not course.invoices.filter(student=user, paid=True).exists():
            raise serializers.ValidationError({'course': 'فقط دانشجویان این دوره می‌توانند نظر ثبت کنند.'})
        return attrs


# -------------------- BANNER / PARTNER --------------------
class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'image', 'priority', 'link', 'is_active', 'start_date', 'end_date', 'created_at']
        read_only_fields = ['created_at']


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['id', 'title', 'logo', 'description', 'link', 'priority', 'is_active', 'created_at']
        read_only_fields = ['created_at']
