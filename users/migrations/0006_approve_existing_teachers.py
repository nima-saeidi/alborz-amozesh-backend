from django.db import migrations


def approve_existing_teachers(apps, schema_editor):
    # Teachers registered before the approval step keep their access
    Teacher = apps.get_model('users', 'Teacher')
    Teacher.objects.update(is_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_persian_labels_teacher_approval_sessions'),
    ]

    operations = [
        migrations.RunPython(approve_existing_teachers, migrations.RunPython.noop),
    ]
