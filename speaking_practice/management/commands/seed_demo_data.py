from django.core.management.base import BaseCommand
from django.db import transaction

from speaking_practice.models import (
    ParentProfile,
    StudentParent,
    StudentProfile,
    StudyClass,
    TeacherProfile,
    TeacherStudent,
    User,
)

TEST_PASSWORD = "Test12345!"

# A small pool of Vietnamese names for realistic demo accounts.
LAST_NAMES = ['Nguyen', 'Tran', 'Le', 'Pham', 'Hoang', 'Huynh', 'Phan', 'Vu',
              'Vo', 'Dang']
FIRST_NAMES = ['An', 'Binh', 'Chi', 'Dung', 'Hai', 'Hoa', 'Hung', 'Lan',
               'Linh', 'Long', 'Mai', 'Minh', 'Nam', 'Ngoc', 'Phuc', 'Thao',
               'Thu', 'Trang', 'Tuan', 'Vy']


def _full_name(i, offset=0):
    return (f"{LAST_NAMES[(i + offset) % len(LAST_NAMES)]} "
            f"{FIRST_NAMES[(i * 3 + offset) % len(FIRST_NAMES)]}")


class Command(BaseCommand):
    help = (
        "Create demo data on top of the existing database (idempotent): "
        "10 teachers, 40 students, 40 parents (password: Test12345!), "
        "teacher-student links, one parent per student, and one sample "
        "class per teacher."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        teachers = []
        for i in range(1, 11):
            username = f"demo_teacher{i}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@example.com",
                          'role': 'teacher',
                          'first_name': _full_name(i).split()[1],
                          'last_name': _full_name(i).split()[0]},
            )
            if created:
                user.set_password(TEST_PASSWORD)
                user.save()
            profile, _ = TeacherProfile.objects.get_or_create(user=user)
            teachers.append(profile)
        self.stdout.write(f"Teachers: {len(teachers)}")

        students = []
        for i in range(1, 41):
            username = f"demo_student{i:02d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@example.com",
                          'role': 'student',
                          'first_name': _full_name(i, 1).split()[1],
                          'last_name': _full_name(i, 1).split()[0]},
            )
            if created:
                user.set_password(TEST_PASSWORD)
                user.save()
            profile, _ = StudentProfile.objects.get_or_create(
                user=user, defaults={'grade_level': f"Grade {6 + (i % 4)}"})
            students.append(profile)
            # Round-robin: each teacher gets 4 students.
            teacher = teachers[(i - 1) % len(teachers)]
            TeacherStudent.objects.get_or_create(teacher=teacher,
                                                 student=profile)
        self.stdout.write(f"Students: {len(students)}")

        for i, student in enumerate(students, start=1):
            username = f"demo_parent{i:02d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f"{username}@example.com",
                          'role': 'parent',
                          'first_name': _full_name(i, 2).split()[1],
                          'last_name': _full_name(i, 2).split()[0]},
            )
            if created:
                user.set_password(TEST_PASSWORD)
                user.save()
            parent, _ = ParentProfile.objects.get_or_create(user=user)
            StudentParent.objects.get_or_create(
                student=student, parent=parent,
                defaults={'relationship_type': 'Father'
                          if i % 2 else 'Mother'})
        self.stdout.write("Parents: 40 (one per student)")

        for i, teacher in enumerate(teachers, start=1):
            study_class, _ = StudyClass.objects.get_or_create(
                name=f"Class {i}", teacher=teacher)
            for student in students[(i - 1) * 4:i * 4]:
                study_class.students.add(student)
        self.stdout.write("Sample classes: 10 (Class 1..10, 4 students each)")

        self.stdout.write(self.style.SUCCESS(
            "Done. All demo accounts use password: Test12345!"))
