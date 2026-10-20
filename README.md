# Alborz Institute Backend

بک‌اند سایت آموزشی البرز — Django 5.2 + Django REST Framework + PostgreSQL + JWT

- مستندات زنده API: `/swagger/` و `/redoc/`
- پنل مدیریت (فارسی): `/admin/`
- همه آدرس‌های API با `/api/` شروع می‌شوند. احراز هویت: هدر `Authorization: Bearer <access>`

## اجرا روی سیستم

```bash
python -m venv venv && source venv/bin/activate      # ویندوز: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # مقادیر را پر کنید (برای تست سریع: DATABASE_URL=sqlite:///db.sqlite3 و DEBUG=True)
python manage.py migrate
python manage.py create_superadmin --email admin@example.com --password 'یک-رمز-قوی'
python manage.py runserver
```

تست‌ها: `python manage.py test`

## API

### احراز هویت با شماره موبایل (سایت)
| متد | آدرس | توضیح |
|---|---|---|
| POST | `/api/auth/phone/check/` | `phone_number` → `exists`, `has_password` (حساب دارد یا نه) |
| POST | `/api/auth/otp/send/` | ارسال کد پیامکی — `phone_number, purpose=register\|login\|reset` (ارسال دوباره بعد از ۲ دقیقه) |
| POST | `/api/auth/otp/verify/` | `phone_number, code, purpose` → برای `login`: توکن‌ها؛ برای `register`/`reset`: `verification_token` (۱۵ دقیقه اعتبار) |
| POST | `/api/auth/phone/register/` | ساخت حساب: `verification_token, first_name, last_name, password, password2, email?` → توکن‌ها |
| POST | `/api/auth/phone/login/` | ورود با `phone_number, password` → توکن‌ها |
| POST | `/api/auth/password/reset/` | رمز جدید: `verification_token, password, password2` → توکن‌ها |

شماره با ارقام فارسی، `+98` و `0098` هم پذیرفته و به شکل `09xxxxxxxxx` ذخیره می‌شود. هر کد ۳ دقیقه اعتبار و حداکثر ۵ بار تلاش دارد.
پیامک با `SMS_BACKEND` در `.env` تعیین می‌شود: `console` (فقط در لاگ؛ در حالت DEBUG کد در پاسخ API هم برمی‌گردد)، `kavenegar` (`KAVENEGAR_API_KEY`, `KAVENEGAR_TEMPLATE`) یا `smsir` (`SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID`؛ نام پارامتر قالب: `Code`).

### احراز هویت با ایمیل (ادمین‌ها و حساب‌های قدیمی)
| متد | آدرس | توضیح |
|---|---|---|
| POST | `/api/auth/register/` | ثبت‌نام دانشجو (`first_name, last_name, email, password, password2, phone_number?`) |
| POST | `/api/auth/teacher-register/` | ثبت‌نام استاد (همان فیلدها + `education_degree, academic_field, bio, profile_image`)؛ بعد از تایید ادمین فعال می‌شود |
| POST | `/api/auth/login/` | ورود با ایمیل و رمز → `access`, `refresh` |
| POST | `/api/auth/token/refresh/` | گرفتن access جدید با `refresh` |
| POST | `/api/auth/logout/` | باطل کردن `refresh` |

### پروفایل
| متد | آدرس | توضیح |
|---|---|---|
| GET | `/api/profile/` | اطلاعات کاربر + دوره‌های ثبت‌نامی |
| PATCH/PUT | `/api/profile/update/` | ویرایش اطلاعات (multipart برای عکس)؛ اساتید: `bio, academic_field, education_degree, teacher_image` |
| PUT | `/api/profile/update/credentials/` | تغییر ایمیل یا رمز (`current_password` الزامی) |

### عمومی (بدون لاگین)
| متد | آدرس | توضیح |
|---|---|---|
| GET | `/api/courses/` | لیست دوره‌ها — `search, category, level, teacher, kind=course\|webinar, max_price, free=1, available=1, ordering=newest\|oldest\|price\|-price\|popular, page, page_size`؛ هر دوره `kind`، `rating` (میانگین نظرات تاییدشده) و `reviews_count` دارد |
| GET | `/api/courses/categories/` | دسته‌بندی‌ها با تعداد |
| GET | `/api/courses/<id>/` | جزئیات دوره + جلسات (+ `is_enrolled`, `is_paid` برای کاربر لاگین) |
| GET | `/api/courses/<id>/sessions/` | جلسات دوره |
| GET | `/api/teachers/` , `/api/teachers/<id>/` | اساتید تایید شده |
| GET | `/api/banners/` , `/api/partners/` , `/api/gallery/` | محتوای صفحه اول |
| GET/POST | `/api/comments/` | نظرات تایید شده (`?course=` یا `?user=`)؛ ثبت نظر برای دانشجوی همان دوره (بعد از تایید ادمین نمایش داده می‌شود) |

**فایل جلسات:** `video_url` و `pdf_url` فقط برای دانشجوی پرداخت‌کرده، استاد دوره و ادمین برگردانده می‌شوند (جلسات `is_free` برای همه). این لینک‌ها امضا شده‌اند و ۶ ساعت اعتبار دارند و مستقیم در `<video src>` قابل استفاده‌اند.

### استانداردهای فنی و حرفه‌ای (عمومی)
| متد | آدرس | توضیح |
|---|---|---|
| GET | `/api/standards/` | لیست منتشرشده‌ها — `search` (عنوان، کد، توضیحات)، `category`، `page`, `page_size` |
| GET | `/api/standards/categories/` | گروه‌هایی که استاندارد منتشرشده دارند + تعداد |
| GET | `/api/standards/<id>/` | جزئیات |
| GET | `/api/standards/<id>/file/` | شمارش دانلود و انتقال به فایل PDF |

فایل‌ها از پنل مدیریت (منوی «استانداردهای فنی و حرفه‌ای») یا API ادمین `standards/` و `standard-categories/` (سطح ۴) آپلود می‌شوند؛ فقط PDF پذیرفته می‌شود.

### دانشجو
| متد | آدرس | توضیح |
|---|---|---|
| POST | `/api/student/enroll/` | ثبت‌نام در دوره (`course_id`) → فاکتور؛ دوره رایگان مستقیم پرداخت‌شده می‌شود |
| DELETE | `/api/student/remove/` | لغو ثبت‌نام پرداخت‌نشده (`course_id`) |
| GET | `/api/student/invoices/` | فاکتورها |
| GET | `/api/student/courses/` | دوره‌های پرداخت‌شده |

### پنل کاربر (`/api/me/`، با لاگین)
| متد | آدرس | توضیح |
|---|---|---|
| GET / POST | `/api/me/favorites/` | شناسه دوره‌های علاقه‌مندی / افزودن (`course` یا `courses: []`) |
| DELETE | `/api/me/favorites/<course_id>/` | حذف از علاقه‌مندی |
| GET | `/api/me/progress/` | جلسات دیده‌شده همه دوره‌ها `{course_id: [session ids]}` |
| GET / POST | `/api/me/progress/<course_id>/` | پیشرفت یک دوره / علامت جلسه (`session`, `done`) |
| GET / POST | `/api/me/certificates/` | گواهی‌ها و پیشرفت دوره‌ها / صدور گواهی (`course`) پس از دیدن همه جلسات |
| GET / POST | `/api/me/tickets/` | تیکت‌ها / تیکت جدید (`subject`, `department`, `course?`, `text`, `attachment?` multipart) |
| GET | `/api/me/tickets/<id>/` | تیکت با پیام‌ها |
| POST | `/api/me/tickets/<id>/reply/` · `/close/` | پاسخ / بستن تیکت |
| GET | `/api/me/notifications/` | اعلان‌ها + تعداد خوانده‌نشده |
| POST | `/api/me/notifications/read/` | خوانده‌شدن (`ids` یا همه) |
| GET / POST | `/api/me/teacher/` | وضعیت / درخواست تدریس (بعد از تایید ادمین فعال می‌شود) |
| GET | `/api/me/teacher/stats/` | آمار پنل استاد |

پاسخ ادمین به تیکت (از بخش «تیکت‌ها» در پنل مدیریت)، تایید پرداخت و صدور گواهی، خودکار برای کاربر اعلان می‌سازد.
اعلانی که در پنل مدیریت بدون کاربر ساخته شود برای همه کاربران نمایش داده می‌شود.

### فرم‌های عمومی
| متد | آدرس | توضیح |
|---|---|---|
| GET | `/api/certificates/<code>/` | استعلام گواهی‌نامه |
| POST | `/api/contact/` | فرم تماس با ما (`name`, `phone` یا `email`, `subject`, `message`) |
| POST | `/api/newsletter/` | عضویت در خبرنامه پیامکی (`phone_number`) |

### استاد (تایید شده)
| متد | آدرس | توضیح |
|---|---|---|
| GET | `/api/teacher/courses/` | دوره‌های من |
| POST | `/api/teacher/courses/create/` | ایجاد دوره (multipart برای `logo`) |
| GET/PUT/PATCH/DELETE | `/api/teacher/courses/<id>/` , `.../update/` , `.../delete/` | مدیریت دوره |
| GET | `/api/teacher/courses/<id>/students/` | دانشجویان دوره |
| GET/POST | `/api/teacher/courses/<id>/sessions/` | جلسات (آپلود `video`, `pdf` با multipart) |
| GET/PATCH/DELETE | `/api/teacher/sessions/<id>/` | ویرایش جلسه |

### ادمین (`/api/admin/`)
سطح دسترسی: ۱ گالری، ۴ مدیریت محتوا و دوره‌ها، ۵ مدیر کل.

`login/`, `me/`, `dashboard/`, `register/` (مدیر کل)، و CRUD کامل برای:
`users/` (۵)، `standards/`، `standard-categories/`، `teachers/` (+ `approve/`, `reject/`)، `courses/`، `sessions/`، `invoices/` (+ `mark-paid/`)، `comment/` (+ `approve/`, `reject/`)، `banner/`، `partner/`، `gallery/` (۱)

## استقرار

فایل‌های نمونه در پوشه `deploy/` است (nginx + systemd + gunicorn). بعد از هر تغییر روی سرور:

```bash
cd /srv/alborz-backend && sudo -u alborz ./deploy/update.sh
```

## کارهای بعدی
- اتصال درگاه پرداخت (زرین‌پال و ...) — فعلاً پرداخت از پنل ادمین ثبت می‌شود (`mark-paid`)
