"""
Sign up / login with a mobile number.

1. POST auth/phone/check/          {phone_number}                    -> does an account exist, does it have a password
2. POST auth/otp/send/             {phone_number, purpose}           -> SMS code (purpose: register | login | reset)
3. POST auth/otp/verify/           {phone_number, code, purpose}     -> login: JWT, register / reset: verification_token
4. POST auth/phone/register/       {verification_token, first_name, last_name, password, password2, email?} -> JWT
   POST auth/phone/login/          {phone_number, password}          -> JWT
   POST auth/password/reset/       {verification_token, password, password2} -> JWT
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import PhoneOTP
from .phone import code_matches, generate_code, hash_code, make_verification_token, normalize_phone, read_verification_token, send_code_sms
from .serializers import validate_unique_email

User = get_user_model()
Purpose = PhoneOTP.Purpose


def find_user(_phone):
    return User.objects.filter(phone_number=_phone).first()


def password_errors(_password, _user):
    try:
        validate_password(_password, _user)
    except Exception as error:
        return list(getattr(error, 'messages', [str(error)]))
    return None


# -------------------- SERIALIZERS --------------------
class PhoneField(serializers.CharField):
    def to_internal_value(self, data):
        phone = normalize_phone(super().to_internal_value(data))
        if phone is None:
            raise serializers.ValidationError('شماره موبایل معتبر نیست (مثال: ۰۹۱۲۱۲۳۴۵۶۷).')
        return phone


class PhoneSerializer(serializers.Serializer):
    phone_number = PhoneField(max_length=20)


class SendCodeSerializer(PhoneSerializer):
    purpose = serializers.ChoiceField(choices=Purpose.choices)


class VerifyCodeSerializer(SendCodeSerializer):
    code = serializers.CharField(max_length=10)


class PhoneLoginSerializer(PhoneSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class NewPasswordSerializer(serializers.Serializer):
    verification_token = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})

    purpose = Purpose.RESET

    def validate(self, attrs):
        phone = read_verification_token(attrs['verification_token'], self.purpose)
        if phone is None:
            raise serializers.ValidationError({'verification_token': 'زمان تایید شماره تمام شده است؛ دوباره کد دریافت کنید.'})
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'رمز عبور و تکرار آن یکسان نیستند.'})
        attrs['phone_number'] = phone
        return attrs


class PhoneRegisterSerializer(NewPasswordSerializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    purpose = Purpose.REGISTER

    def validate_email(self, value):
        return validate_unique_email(value) if value else None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if find_user(attrs['phone_number']):
            raise serializers.ValidationError({'phone_number': 'با این شماره قبلاً حساب ساخته شده است؛ وارد شوید.'})
        candidate = User(username=attrs['phone_number'], first_name=attrs['first_name'], last_name=attrs['last_name'], email=attrs.get('email'))
        errors = password_errors(attrs['password'], candidate)
        if errors:
            raise serializers.ValidationError({'password': errors})
        return attrs

    def create(self, validated_data):
        user = User(
            username=validated_data['phone_number'],
            phone_number=validated_data['phone_number'],
            email=validated_data.get('email') or None,
            first_name=validated_data['first_name'].strip(),
            last_name=validated_data['last_name'].strip(),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


# -------------------- VIEWS --------------------
def jwt_response(user, _status=status.HTTP_200_OK):
    from .views import generate_jwt_response  # avoid a circular import
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])
    return Response(generate_jwt_response(user), status=_status)


class PhoneCheckAPIView(generics.GenericAPIView):
    serializer_class = PhoneSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']
        user = find_user(phone)
        return Response({
            'phone_number': phone,
            'exists': user is not None,
            'has_password': bool(user and user.has_usable_password()),
        })


class SendCodeAPIView(generics.GenericAPIView):
    serializer_class = SendCodeSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'otp'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']
        purpose = serializer.validated_data['purpose']

        user = find_user(phone)
        if purpose == Purpose.REGISTER and user:
            return Response({'detail': 'با این شماره قبلاً حساب ساخته شده است؛ وارد شوید.', 'code': 'exists'}, status=status.HTTP_400_BAD_REQUEST)
        if purpose != Purpose.REGISTER and (user is None or not user.is_active):
            return Response({'detail': 'حسابی با این شماره پیدا نشد؛ ابتدا ثبت‌نام کنید.', 'code': 'not_found'}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        recent = PhoneOTP.objects.filter(phone_number=phone, created_at__gte=now - timedelta(hours=1))
        last = recent.first()
        if last and (now - last.created_at).total_seconds() < settings.OTP_RESEND_SECONDS:
            wait = settings.OTP_RESEND_SECONDS - int((now - last.created_at).total_seconds())
            return Response({'detail': f'برای ارسال دوباره {wait} ثانیه صبر کنید.', 'resend_in': wait}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if recent.count() >= settings.OTP_MAX_PER_HOUR:
            return Response({'detail': 'تعداد درخواست کد زیاد است؛ یک ساعت دیگر تلاش کنید.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        code = generate_code()
        with transaction.atomic():
            PhoneOTP.objects.filter(phone_number=phone, purpose=purpose, is_used=False).update(is_used=True)
            PhoneOTP.objects.create(phone_number=phone, purpose=purpose, code_hash=hash_code(phone, code))
        if not send_code_sms(phone, code):
            return Response({'detail': 'ارسال پیامک انجام نشد؛ کمی بعد دوباره تلاش کنید.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        data = {
            'detail': 'کد تایید پیامک شد.',
            'phone_number': phone,
            'expires_in': settings.OTP_TTL_SECONDS,
            'resend_in': settings.OTP_RESEND_SECONDS,
        }
        if settings.DEBUG and settings.SMS_BACKEND == 'console' and settings.OTP_RETURN_CODE_IN_DEBUG:
            data['debug_code'] = code
        return Response(data)


class VerifyCodeAPIView(generics.GenericAPIView):
    serializer_class = VerifyCodeSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'otp_verify'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone_number']
        purpose = serializer.validated_data['purpose']

        otp = PhoneOTP.objects.filter(phone_number=phone, purpose=purpose, is_used=False).first()
        expired = otp is None or (timezone.now() - otp.created_at).total_seconds() > settings.OTP_TTL_SECONDS
        if expired or otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            return Response({'detail': 'کد منقضی شده است؛ کد جدید دریافت کنید.', 'code': 'expired'}, status=status.HTTP_400_BAD_REQUEST)

        if not code_matches(otp, serializer.validated_data['code']):
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            left = settings.OTP_MAX_ATTEMPTS - otp.attempts
            return Response({'detail': f'کد وارد شده اشتباه است ({left} تلاش باقی مانده).', 'code': 'invalid'}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save(update_fields=['is_used'])

        if purpose == Purpose.LOGIN:
            user = find_user(phone)
            if user is None or not user.is_active:
                return Response({'detail': 'حسابی با این شماره پیدا نشد.'}, status=status.HTTP_400_BAD_REQUEST)
            return jwt_response(user)
        return Response({'verification_token': make_verification_token(phone, purpose), 'phone_number': phone})


class PhoneRegisterAPIView(generics.GenericAPIView):
    serializer_class = PhoneRegisterSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return jwt_response(serializer.save(), status.HTTP_201_CREATED)


class PhoneLoginAPIView(generics.GenericAPIView):
    serializer_class = PhoneLoginSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = find_user(serializer.validated_data['phone_number'])
        if user is None or not user.is_active or not user.check_password(serializer.validated_data['password']):
            return Response({'detail': 'شماره موبایل یا رمز عبور اشتباه است.'}, status=status.HTTP_401_UNAUTHORIZED)
        return jwt_response(user)


class PasswordResetAPIView(generics.GenericAPIView):
    serializer_class = NewPasswordSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = find_user(serializer.validated_data['phone_number'])
        if user is None or not user.is_active:
            return Response({'detail': 'حسابی با این شماره پیدا نشد.'}, status=status.HTTP_400_BAD_REQUEST)
        errors = password_errors(serializer.validated_data['password'], user)
        if errors:
            return Response({'password': errors}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return jwt_response(user)
