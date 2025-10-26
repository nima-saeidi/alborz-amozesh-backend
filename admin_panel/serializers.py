from rest_framework import serializers
from django.contrib.auth.hashers import check_password
from users.models import User
from .models import AdminProfile
from django.contrib.auth.password_validation import validate_password

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ('user', 'register_datetime', 'activity_history', 'access_level')
        
        
# -------------- SuperAdminRegistration --------------
class AdminRegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    access_level = serializers.ChoiceField(choices=AdminProfile.ACCESS_LEVEL_CHOICES)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password', 'access_level')

    def create(self, validated_data):
        access_level = validated_data.pop('access_level')
        user = User.objects.create(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()

        AdminProfile.objects.create(user=user, access_level=access_level)
        return user
