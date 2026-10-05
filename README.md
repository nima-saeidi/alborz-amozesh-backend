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

### احراز هویت
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
| GET | `/api/courses/` | لیست دوره‌ها — `search, category, level, teacher, ordering=newest\|oldest\|price\|-price\|popular, page, page_size` |
| GET | `/api/courses/categories/` | دسته‌بندی‌ها با تعداد |
| GET | `/api/courses/<id>/` | جزئیات دوره + جلسات (+ `is_enrolled`, `is_paid` برای کاربر لاگین) |
| GET | `/api/courses/<id>/sessions/` | جلسات دوره |
| GET | `/api/teachers/` , `/api/teachers/<id>/` | اساتید تایید شده |
| GET | `/api/banners/` , `/api/partners/` , `/api/gallery/` | محتوای صفحه اول |
| GET/POST | `/api/comments/` | نظرات تایید شده (`?course=` یا `?user=`)؛ ثبت نظر برای دانشجوی همان دوره (بعد از تایید ادمین نمایش داده می‌شود) |

**فایل جلسات:** `video_url` و `pdf_url` فقط برای دانشجوی پرداخت‌کرده، استاد دوره و ادمین برگردانده می‌شوند (جلسات `is_free` برای همه). این لینک‌ها امضا شده‌اند و ۶ ساعت اعتبار دارند و مستقیم در `<video src>` قابل استفاده‌اند.

### دانشجو
| متد | آدرس | توضیح |
|---|---|---|
| POST | `/api/student/enroll/` | ثبت‌نام در دوره (`course_id`) → فاکتور؛ دوره رایگان مستقیم پرداخت‌شده می‌شود |
| DELETE | `/api/student/remove/` | لغو ثبت‌نام پرداخت‌نشده (`course_id`) |
| GET | `/api/student/invoices/` | فاکتورها |
| GET | `/api/student/courses/` | دوره‌های پرداخت‌شده |

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
`users/` (۵)، `teachers/` (+ `approve/`, `reject/`)، `courses/`، `sessions/`، `invoices/` (+ `mark-paid/`)، `comment/` (+ `approve/`, `reject/`)، `banner/`، `partner/`، `gallery/` (۱)

## استقرار

فایل‌های نمونه در پوشه `deploy/` است (nginx + systemd + gunicorn). بعد از هر تغییر روی سرور:

```bash
cd /srv/alborz-backend && sudo -u alborz ./deploy/update.sh
```

## کارهای بعدی
- اتصال درگاه پرداخت (زرین‌پال و ...) — فعلاً پرداخت از پنل ادمین ثبت می‌شود (`mark-paid`)
