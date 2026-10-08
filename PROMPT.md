We are building a new web application called "English Speaking Practice".

You are working directly inside the current project folder.

Before doing anything, inspect the current directory and existing files. Do not assume the folder is empty.

GOAL

Build the initial Django foundation for an English speaking learning platform.

TECHNOLOGY

- Python
- Django
- Django REST Framework
- PostgreSQL-ready configuration
- HTML/CSS/JavaScript
- Django Templates for the initial UI
- Environment variables for configuration and secrets
- Do NOT hard-code API keys or passwords

IMPORTANT

This is Phase 1 only.

Do NOT implement:
- Speech recognition
- AI pronunciation scoring
- AI grammar analysis
- Fluency analysis
- AI chatbot
- ELSA-like advanced features

PHASE 1

1. DJANGO PROJECT

Create a clean Django project structure suitable for future expansion.

2. AUTHENTICATION

Create a custom Django User model from the beginning.

The system has exactly these roles:

- ADMIN
- TEACHER
- STUDENT
- PARENT

Use Django authentication properly.

3. USER PROFILES

Create appropriate profile models for:

- Teacher
- Student
- Parent

Do not duplicate authentication information unnecessarily.

4. TEACHER / STUDENT

An admin must be able to assign students to teachers.

A teacher can have multiple students.

A student can have one primary teacher for now.

5. PARENT / STUDENT

A parent account must be mapped to the appropriate student.

For the initial version:

- One parent can have one or more children.
- A student can have one or more parents if appropriate.
- Parents must ONLY be able to access their own children's information.

This permission must be enforced on the backend, not only hidden in the frontend.

6. LESSON SYSTEM

Create a flexible lesson structure:

Course
    -> Chapter
        -> Lesson
            -> Exercise

The design must allow future customization.

Exercise should support fields such as:

- title
- description
- instructions
- expected_text
- reference_audio
- image
- order
- is_active
- created_at
- updated_at

Do not over-engineer this part.

7. SPEAKING PREPARATION

Create a basic SpeakingAttempt model.

Do NOT implement AI analysis yet.

It should eventually support:

- student
- exercise
- recorded_audio
- transcript
- grammar_score
- pronunciation_score
- fluency_score
- accuracy_score
- total_score
- feedback
- created_at

Analysis fields can initially be null.

8. DASHBOARDS

Create basic dashboards.

ADMIN DASHBOARD

- total users
- total students
- total teachers
- total parents
- management links

TEACHER DASHBOARD

- assigned students
- available lessons

STUDENT DASHBOARD

- assigned lessons
- basic learning progress placeholder

PARENT DASHBOARD

- own children only
- basic learning progress placeholder

9. DJANGO ADMIN

Configure Django Admin for:

- Users
- Teacher profiles
- Student profiles
- Parent profiles
- Teacher/Student assignment
- Parent/Student mapping
- Courses
- Chapters
- Lessons
- Exercises
- Speaking attempts

Admin should be able to manage relationships easily.

10. PERMISSIONS

Implement backend role-based access.

ADMIN:
- full access

TEACHER:
- teacher dashboard
- assigned students
- manage lessons they own/create
- cannot manage system users

STUDENT:
- own learning data only
- assigned lessons
- create own speaking attempts

PARENT:
- own children only
- read-only access to children's learning information

Do not rely only on frontend restrictions.

11. UI

Create a simple clean responsive interface.

Create:

- login page
- logout
- base template
- navigation
- dashboard pages
- lesson list
- lesson detail
- basic student progress page

Do not spend excessive effort on visual design yet.

12. PROJECT CONFIGURATION

Create:

- requirements.txt
- .env.example
- .gitignore
- README.md

Use environment variables for:

- SECRET_KEY
- DEBUG
- DATABASE_URL or PostgreSQL configuration
- ALLOWED_HOSTS

For development, make it easy to run with SQLite if PostgreSQL is not configured yet.

13. MIGRATIONS

Create required migrations.

Run:

python manage.py check

python manage.py makemigrations

python manage.py migrate

Fix errors if they occur.

14. ADMIN

Make it easy to create an admin account using:

python manage.py createsuperuser

Do not create fake production users.

15. CODE QUALITY

Follow Django best practices.

Use clear model names.

Use useful related_name values.

Add useful __str__ methods.

Add model Meta ordering where appropriate.

Avoid unnecessary abstractions.

Avoid duplicated code.

Keep the project easy for another developer to understand.

IMPORTANT WORKFLOW RULES

- First inspect the current directory.
- Then create the project structure.
- Before editing an existing file, read it first.
- Do not delete unrelated existing files.
- Do not overwrite existing code blindly.
- If something already exists, adapt it instead of recreating it.
- After implementation, run Django checks and migrations.
- If an error occurs, diagnose and fix it.
- At the end, summarize all files created/modified and explain how to run the project.

Do the work directly in the current folder.