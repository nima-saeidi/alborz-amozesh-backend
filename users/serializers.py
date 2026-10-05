from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .access import can_access_course_files, can_access_session_files, make_session_file_url
from .models import Teacher, Course, CourseSession, Invoice

User = get_user_model()


def normalize_email(_email):
    return _email.strip().lower()


def validate_unique_email(_email, _exclude_user=None):
    email = normalize_email(_email)
    queryset = User.objects.filter(email__iexact=email)
    if _exclude_user is not None:
        queryset = queryset.exclude(pk=_exclude_user.pk)
    if queryset.exists():
        raise serializers.ValidationError('این ایمیل قبلاً ثبت شده است.')
    return email


# -------------------- REGISTRATION --------------------
class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, label='Confirm password', style={'input_type': 'password'})

    def validate_email(self, value):
        return validate_unique_email(value)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'رمز عبور و تکرار آن یکسان نیستند.'})
        candidate = User(email=attrs['email'], first_name=attrs['first_name'], last_name=attrs['last_name'])
        try:
            validate_password(attrs['password'], candidate)
        except Exception as error:
            raise serializers.ValidationError({'password': list(getattr(error, 'messages', [str(error)]))})
        return attrs

    def create_user(self, validated_data):
        user = User(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data.get('phone_number') or None,
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

    def create(self, validated_data):
        return self.create_user(validated_data)


class TeacherRegisterSerializer(RegisterSerializer):
    """Flat payload (multipart friendly). The teacher must be approved by an admin before managing courses"""
    education_degree = serializers.CharField(max_length=100, required=False, allow_blank=True)
    academic_field = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    @transaction.atomic
    def create(self, validated_data):
        user = self.create_user(validated_data)
        teacher = Teacher.objects.create(
            user=user,
            education_degree=validated_data.get('education_degree') or None,
            academic_field=validated_data.get('academic_field') or None,
            bio=validated_data.get('bio') or None,
            profile_image=validated_data.get('profile_image'),
            is_approved=False,
        )
        return teacher


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# -------------------- CREDENTIALS --------------------
class UpdateCredentialsSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(required=False)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['current_password']):
            raise serializers.ValidationError({'current_password': 'رمز عبور فعلی اشتباه است.'})
        if attrs.get('email'):
            attrs['email'] = validate_unique_email(attrs['email'], _exclude_user=user)
        if attrs.get('new_password'):
            try:
                validate_password(attrs['new_password'], user)
            except Exception as error:
                raise serializers.ValidationError({'new_password': list(getattr(error, 'messages', [str(error)]))})
        if not attrs.get('email') and not attrs.get('new_password'):
            raise serializers.ValidationError('ایمیل جدید یا رمز عبور جدید را وارد کنید.')
        return attrs


# -------------------- TEACHER (public) --------------------
class TeacherBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'full_name', 'academic_field', 'profile_image']


class TeacherPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    courses_count = serializers.IntegerField(read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'full_name', 'first_name', 'last_name', 'education_degree', 'academic_field', 'bio', 'profile_image', 'courses_count', 'rating']

    def get_rating(self, obj):
        return round(float(obj.user.popularity), 1)


# -------------------- PROFILE --------------------
class UserProfileSerializer(serializers.ModelSerializer):
    is_teacher = serializers.BooleanField(read_only=True)
    teacher_profile = serializers.SerializerMethodField()
    selected_courses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone_number', 'birthday_date',
            'national_id', 'gender', 'fathers_name', 'education_level', 'profile_image',
            'is_teacher', 'teacher_profile', 'selected_courses', 'date_joined'
        ]
        read_only_fields = ['email', 'date_joined']

    def get_teacher_profile(self, obj):
        if not hasattr(obj, 'teacher'):
            return None
        teacher = obj.teacher
        return {
            'id': teacher.id,
            'is_approved': teacher.is_approved,
            'education_degree': teacher.education_degree,
            'academic_field': teacher.academic_field,
            'bio': teacher.bio,
        }

    def get_selected_courses(self, obj):
        return [
            {'id': invoice.course_id, 'title': invoice.course.title, 'paid': invoice.paid}
            for invoice in obj.invoices.select_related('course')
        ]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Personal info of any user + teacher info when the user is a teacher"""
    profile_image = serializers.ImageField(required=False, allow_null=True)
    education_degree = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    academic_field = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    teacher_image = serializers.ImageField(required=False, allow_null=True)

    TEACHER_FIELDS = ('education_degree', 'academic_field', 'bio')

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'birthday_date', 'national_id', 'gender',
            'fathers_name', 'education_level', 'profile_image',
            'education_degree', 'academic_field', 'bio', 'teacher_image'
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        teacher_data = {key: validated_data.pop(key) for key in self.TEACHER_FIELDS if key in validated_data}
        teacher_image = validated_data.pop('teacher_image', None)

        instance = super().update(instance, validated_data)

        if hasattr(instance, 'teacher') and (teacher_data or teacher_image):
            teacher = instance.teacher
            for key, value in teacher_data.items():
                setattr(teacher, key, value)
            if teacher_image:
                teacher.profile_image = teacher_image
            teacher.save()

        return instance

    def to_representation(self, instance):
        return UserProfileSerializer(instance, context=self.context).data


# -------------------- SESSIONS --------------------
class CourseSessionSerializer(serializers.ModelSerializer):
    """
    Public representation: file links are only given to users allowed to see them
    (context['course_access'] can be precomputed for the whole course)
    """
    has_video = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = CourseSession
        fields = ['id', 'title', 'description', 'order', 'is_free', 'has_video', 'has_pdf', 'video_url', 'pdf_url', 'created_at']

    def get_has_video(self, obj):
        return bool(obj.video)

    def get_has_pdf(self, obj):
        return bool(obj.pdf)

    def _can_access(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return can_access_session_files(user, obj, self.context.get('course_access'))

    def _file_url(self, obj, kind):
        if not getattr(obj, kind) or not self._can_access(obj):
            return None
        return make_session_file_url(self.context.get('request'), obj, kind)

    def get_video_url(self, obj):
        return self._file_url(obj, 'video')

    def get_pdf_url(self, obj):
        return self._file_url(obj, 'pdf')


class TeacherSessionSerializer(CourseSessionSerializer):
    """Create / update a session (files uploaded with multipart)"""
    video = serializers.FileField(required=False, allow_null=True, write_only=True)
    pdf = serializers.FileField(required=False, allow_null=True, write_only=True)

    class Meta(CourseSessionSerializer.Meta):
        fields = CourseSessionSerializer.Meta.fields + ['course', 'video', 'pdf']
        read_only_fields = ['course']


# -------------------- COURSES --------------------
class CourseListSerializer(serializers.ModelSerializer):
    teacher = TeacherBriefSerializer(read_only=True)
    total_students = serializers.IntegerField(read_only=True)
    sessions_count = serializers.IntegerField(read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'short_description', 'category', 'level', 'tags', 'logo',
            'cost', 'discount_price', 'final_price', 'teacher', 'start_date', 'end_date',
            'duration', 'limit_students', 'total_students', 'sessions_count', 'is_full', 'rating_avg'
        ]

    def get_is_full(self, obj):
        total = getattr(obj, 'total_students', None)
        if total is None:
            total = obj.invoices.filter(paid=True).count()
        return obj.limit_students is not None and total >= obj.limit_students


class CourseDetailSerializer(CourseListSerializer):
    sessions = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            'description', 'requirements', 'exam_date', 'sessions', 'is_enrolled', 'is_paid', 'created_at', 'last_updated'
        ]

    def _invoice(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if not hasattr(self, '_invoice_cache'):
            self._invoice_cache = obj.invoices.filter(student=request.user).first()
        return self._invoice_cache

    def get_sessions(self, obj):
        request = self.context.get('request')
        access = can_access_course_files(getattr(request, 'user', None), obj)
        return CourseSessionSerializer(obj.sessions.all(), many=True, context={**self.context, 'course_access': access}).data

    def get_is_enrolled(self, obj):
        return self._invoice(obj) is not None

    def get_is_paid(self, obj):
        invoice = self._invoice(obj)
        return bool(invoice and invoice.paid)


class TeacherCourseSerializer(serializers.ModelSerializer):
    """Course written by its teacher (the teacher is the logged in user)"""
    teacher = TeacherBriefSerializer(read_only=True)
    total_students = serializers.SerializerMethodField()
    sessions = CourseSessionSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'short_description', 'category', 'level', 'tags', 'logo',
            'cost', 'discount_price', 'requirements', 'start_date', 'end_date', 'exam_date', 'duration',
            'limit_students', 'is_active', 'teacher', 'total_students', 'sessions', 'rating_avg',
            'created_at', 'last_updated'
        ]
        read_only_fields = ['rating_avg', 'created_at', 'last_updated']

    def get_total_students(self, obj):
        return obj.invoices.filter(paid=True).count()

    def validate(self, attrs):
        cost = attrs.get('cost', getattr(self.instance, 'cost', None))
        discount = attrs.get('discount_price', getattr(self.instance, 'discount_price', None))
        if cost is not None and discount is not None and discount > cost:
            raise serializers.ValidationError({'discount_price': 'قیمت با تخفیف نمی‌تواند از قیمت اصلی بیشتر باشد.'})
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'تاریخ پایان باید بعد از تاریخ شروع باشد.'})
        return attrs


# Kept for backward compatibility (admin API)
CourseSerializer = TeacherCourseSerializer


# -------------------- INVOICES --------------------
class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 'amount', 'paid', 'paid_at', 'grade', 'score', 'date_time']
        read_only_fields = fields


class EnrollSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()


# -------------------- TEACHER (full) --------------------
class TeacherSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'education_degree', 'academic_field', 'bio', 'profile_image', 'is_approved']
