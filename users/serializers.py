from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from .models import Teacher, Course, CourseSession, Invoice

User = get_user_model()

# -------------------- USER REGISTRATION --------------------
class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create(
            username=validated_data['email'],  # Email as username
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

# -------------------- TEACHER REGISTRATION --------------------
class TeacherRegisterSerializer(serializers.ModelSerializer):
    user = BaseRegisterSerializer()

    class Meta:
        model = Teacher
        fields = ['user', 'education_degree', 'academic_field', 'bio', 'profile_image']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = BaseRegisterSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        teacher = Teacher.objects.create(user=user, **validated_data)
        return teacher

# -------------------- LOGIN --------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# -------------------- UPDATE CREDENTIALS --------------------
class UpdateCredentialsSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(required=False)

# -------------------- USER / STUDENT PROFILE --------------------
class UserProfileSerializer(serializers.ModelSerializer):
    selected_courses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'birthday_date',
            'national_id', 'gender', 'fathers_name', 'education_level', 'profile_image',
            'selected_courses'
        ]

    def get_selected_courses(self, obj):
        invoices = Invoice.objects.filter(student=obj)
        return [invoice.course.title for invoice in invoices]

class StudentUpdateProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False)  

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'birthday_date',
            'national_id', 'gender', 'fathers_name', 'education_level', 'profile_image'
        ]

class TeacherUpdateProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = Teacher
        fields = ['education_degree', 'academic_field', 'bio', 'profile_image']

# -------------------- COURSE SESSION SERIALIZER --------------------
class CourseSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSession
        fields = ['id', 'title', 'description', 'video', 'pdf', 'created_at']

# -------------------- COURSE SERIALIZER --------------------
# -------------------- COURSE SERIALIZER --------------------
class CourseSerializer(serializers.ModelSerializer):
    sessions = CourseSessionSerializer(many=True, read_only=True)
    total_students = serializers.SerializerMethodField()
    teacher = serializers.ReadOnlyField(source='teacher.id')  

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'short_description', 'category', 'level',
            'cost', 'discount_price', 'logo', 'tags', 'requirements',
            'teacher', 'sessions', 'total_students', 'start_date', 'end_date',
            'limit_students', 'rating_avg'
        ]

    def get_total_students(self, obj):
        return obj.invoices.count()
# -------------------- INVOICE SERIALIZER --------------------
class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 'paid', 'grade', 'score', 'date_time']

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

# -------------------- TEACHER SERIALIZER --------------------
class TeacherSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()

    class Meta:
        model = Teacher
        fields = ['id', 'user', 'education_degree', 'academic_field', 'bio', 'profile_image']
