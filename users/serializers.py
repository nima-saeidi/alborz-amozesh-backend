# ===========================================
# users/serializers.py
# ===========================================
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password
from .models import Course, Teacher, Invoice, User

User = get_user_model()
# -------------------- Base Register Serializer --------------------
class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    email = serializers.EmailField(required=True)  

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def validate_email(self, value):
        """Check that the email is unique and not empty"""
        if not value:
            raise serializers.ValidationError("Email is required.")
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        user = self.Meta.model.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            username=validated_data['email']  # username = email
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

# -------------------- Teacher Register Serializer --------------------
class TeacherRegisterSerializer(BaseRegisterSerializer):
    # Do NOT include education_degree in Meta.fields because it's not in User model

    def create(self, validated_data):
        # Create user first
        user_data = {
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'email': validated_data['email'],
            'username': validated_data['email'],
        }
        user = User.objects.create(**user_data)
        user.set_password(validated_data['password'])
        user.save()

        # Then create Teacher instance
        teacher = Teacher.objects.create(
            user=user,
            education_degree=validated_data.get('education_degree', ''),  # optional
        )
        return user


# -------------------- Login Serializer --------------------
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# -------------------- Base Update Profile Serializer --------------------
class BaseUpdateProfileSerializer(serializers.ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not check_password(value, user.password):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def update(self, instance, validated_data):
        validated_data.pop('current_password', None)  # remove password field
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# -------------------- Teacher Update Profile --------------------
class TeacherUpdateProfileSerializer(BaseUpdateProfileSerializer):
    class Meta:
        model = Teacher
        fields = (
            'education_degree', 'academic_field', 'bio', 'profile_image', 'current_password'
        )

    def update(self, instance, validated_data):
        # check_password روی User
        current_password = validated_data.pop('current_password', None)
        user = instance.user
        if current_password and not check_password(current_password, user.password):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})

        # update Teacher fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

# -------------------- Student Update Profile --------------------
class StudentUpdateProfileSerializer(BaseUpdateProfileSerializer):
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'birthday_date', 'national_id',
            'gender', 'fathers_name', 'education_level', 'profile_image', 'current_password'
        )

# -------------------- Course Serializer --------------------
class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'teacher_name', 'start_date', 'end_date', 'duration',
            'cost', 'level', 'category', 'tags', 'description', 'short_description',
            'is_active', 'limit_students', 'discount_price'
        ]

    def get_teacher_name(self, obj):
        return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"


# -------------------- Teacher Serializer --------------------
class TeacherSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'user_name', 'education_degree', 'academic_field', 'bio', 'profile_image']

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


# -------------------- User Profile Serializer --------------------
class UserProfileSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'birthday_date', 'national_id',
            'gender', 'fathers_name', 'education_level', 'profile_image', 'courses'
        ]

    def get_courses(self, obj):
        invoices = Invoice.objects.filter(student=obj)
        return CourseSerializer([invoice.course for invoice in invoices], many=True).data