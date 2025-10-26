# ===========================================
# users/serializers.py
# ===========================================
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import check_password
from .models import Teacher

User = get_user_model()

# -------------------- Base Register Serializer --------------------
class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        # Create user and hash password
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
    class Meta(BaseRegisterSerializer.Meta):
        fields = BaseRegisterSerializer.Meta.fields + ('education_level',)

    def create(self, validated_data):
        user_data = {
            'first_name': validated_data['first_name'],
            'last_name': validated_data['last_name'],
            'email': validated_data['email'],
            'username': validated_data['email'],
        }
        user = User.objects.create(**user_data)
        user.set_password(validated_data['password'])
        user.save()

        teacher = Teacher.objects.create(
            user=user,
            education_degree=validated_data.get('education_level', ''),
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


# -------------------- Student Update Profile --------------------
class StudentUpdateProfileSerializer(BaseUpdateProfileSerializer):
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'birthday_date', 'national_id',
            'gender', 'fathers_name', 'education_level', 'profile_image', 'current_password'
        )
