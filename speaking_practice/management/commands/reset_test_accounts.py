from django.core.management.base import BaseCommand
from django.db import transaction

from speaking_practice.models import (
    Chapter,
    Course,
    Exercise,
    Lesson,
    ParentProfile,
    StudentLesson,
    StudentParent,
    StudentProfile,
    TeacherProfile,
    TeacherStudent,
    User,
)

TEST_PASSWORD = "Test12345!"


class Command(BaseCommand):
    help = (
        "Delete ALL users (and their related data) and recreate one fresh "
        "test account per role: admin / teacher1 / student1 / parent1 "
        "(password: Test12345!), with linked profiles and a sample lesson."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the confirmation prompt.",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            confirm = input(
                "This will DELETE ALL users and their related data. "
                "Type YES to continue: "
            )
            if confirm.strip() != "YES":
                self.stdout.write(self.style.WARNING("Aborted. Nothing was deleted."))
                return

        with transaction.atomic():
            deleted_count, _ = User.objects.all().delete()
            self.stdout.write(f"Deleted {deleted_count} object(s) (all users + related data).")

            admin = User.objects.create_user(
                username="admin",
                email="admin@example.com",
                password=TEST_PASSWORD,
                role="admin",
                is_staff=True,
                is_superuser=True,
            )
            teacher_user = User.objects.create_user(
                username="teacher1",
                email="teacher1@example.com",
                password=TEST_PASSWORD,
                role="teacher",
            )
            student_user = User.objects.create_user(
                username="student1",
                email="student1@example.com",
                password=TEST_PASSWORD,
                role="student",
            )
            parent_user = User.objects.create_user(
                username="parent1",
                email="parent1@example.com",
                password=TEST_PASSWORD,
                role="parent",
            )

            teacher = TeacherProfile.objects.create(
                user=teacher_user, bio="Test teacher account."
            )
            student = StudentProfile.objects.create(
                user=student_user, grade_level="Grade 7"
            )
            parent = ParentProfile.objects.create(
                user=parent_user, relationship_to_child="Father"
            )

            TeacherStudent.objects.create(teacher=teacher, student=student)
            StudentParent.objects.create(
                student=student, parent=parent, relationship_type="Father"
            )

            course = Course.objects.create(
                title="Test Course",
                description="Sample course for testing.",
            )
            chapter = Chapter.objects.create(
                course=course, title="Chapter 1: Greetings", order=1
            )
            lesson = Lesson.objects.create(
                chapter=chapter,
                teacher=teacher,
                title="Saying hello",
                description="Practice greeting people in English.",
                order=1,
            )
            Exercise.objects.create(
                lesson=lesson,
                title="Introduce yourself",
                instructions="Say the sentence out loud, then record yourself.",
                expected_text="Hello! My name is Anna. Nice to meet you.",
                order=1,
            )
            StudentLesson.objects.create(student=student, lesson=lesson)

        self.stdout.write(self.style.SUCCESS("Done. Test accounts (password: Test12345!):"))
        for username, role in [
            ("admin", "admin"),
            ("teacher1", "teacher"),
            ("student1", "student"),
            ("parent1", "parent"),
        ]:
            self.stdout.write(f"  - {username} ({role})")
        self.stdout.write("Sample data: 1 course, 1 chapter, 1 lesson, 1 exercise,")
        self.stdout.write("teacher1 linked to student1, parent1 linked to student1,")
        self.stdout.write("and the lesson assigned to student1.")
