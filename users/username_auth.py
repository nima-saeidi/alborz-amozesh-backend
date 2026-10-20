"""
Sign up / login with a username and password (no mobile number needed).

POST auth/username/check/      {username}                                             -> is it free
POST auth/username/register/   {username, first_name, last_name, password, password2, email?} -> JWT
POST auth/username/login/      {username, password}  (username, email or mobile)      -> JWT
"""
import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .phone import normalize_phone
from .phone_auth import jwt_response, password_errors
from .serializers import validate_unique_email

User = get_user_model()

# Starts with a letter, so it never collides with mobile-number usernames (09xxxxxxxxx)
USERNAME_RE = re.compile(r'^[a-z][a-z0-9_.]{2,29}$')
RESERVED = {'admin', 'administrator', 'root', 'support', 'alborz', 'staff', 'api', 'null'}


def find_login_user(_identifier):
    """A user by username, email or mobile number"""
    identifier = _identifier.strip()
    query = Q(username__iexact=identifier) | Q(email__iexact=identifier)
    phone = normalize_phone(identifier)
    if phone:
        query |= Q(phone_number=phone)
    return User.objects.filter(query).order_by('id').first()


class UsernameField(serializers.CharField):
    def to_internal_value(self, data):
        username = super().to_internal_value(data).strip().lower()
        if not USERNAME_RE.match(username):
            raise serializers.ValidationError('نام کاربری باید ۳ تا ۳۰ کاراکتر انگلیسی باشد، با حرف شروع شود و فقط شامل حروف، عدد، _ و . باشد.')
        if username in RESERVED:
            raise serializers.ValidationError('این نام کاربری قابل استفاده نیست.')
        return username


class UsernameCheckSerializer(serializers.Serializer):
    username = UsernameField(max_length=30)


class UsernameRegisterSerializer(serializers.Serializer):
    username = UsernameField(max_length=30)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('این نام کاربری قبلاً گرفته شده است.')
        return value

    def validate_email(self, value):
        return validate_unique_email(value) if value else None

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'رمز عبور و تکرار آن یکسان نیستند.'})
        candidate = User(username=attrs['username'], first_name=attrs['first_name'], last_name=attrs['last_name'], email=attrs.get('email'))
        errors = password_errors(attrs['password'], candidate)
        if errors:
            raise serializers.ValidationError({'password': errors})
        return attrs

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email') or None,
            first_name=validated_data['first_name'].strip(),
            last_name=validated_data['last_name'].strip(),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UsernameLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, help_text='نام کاربری، ایمیل یا شماره موبایل')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class UsernameCheckAPIView(generics.GenericAPIView):
    serializer_class = UsernameCheckSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        return Response({'username': username, 'available': not User.objects.filter(username__iexact=username).exists()})


class UsernameRegisterAPIView(generics.GenericAPIView):
    serializer_class = UsernameRegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return jwt_response(serializer.save(), status.HTTP_201_CREATED)


class UsernameLoginAPIView(generics.GenericAPIView):
    serializer_class = UsernameLoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = find_login_user(serializer.validated_data['username'])
        if user is None or not user.is_active or not user.check_password(serializer.validated_data['password']):
            return Response({'detail': 'نام کاربری یا رمز عبور اشتباه است.'}, status=status.HTTP_401_UNAUTHORIZED)
        return jwt_response(user)
