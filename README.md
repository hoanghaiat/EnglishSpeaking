# English Speaking Practice

An application for practicing English speaking skills with structured lessons and progress tracking.

## Features

- Role-based access (Admin, Teacher, Student, Parent)
- Lesson management system (Course > Chapter > Lesson > Exercise)
- Speaking practice with attempt tracking
- Dashboard for each user role

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and configure your settings
6. Run migrations: `python manage.py migrate`
7. Create a superuser: `python manage.py createsuperuser`
8. Start the development server: `python manage.py runserver`

### Usage

1. Visit `http://localhost:8000/` to access the application
2. Login with your credentials (or sign up for a student/teacher/parent account)
3. Access different dashboards based on your role:
   - Admin dashboard for managing users and content
   - Teacher dashboard for managing students and lessons
   - Student dashboard for accessing lessons and practicing speaking
   - Parent dashboard for viewing children's progress

## Project Structure

- `english_speaking_app/` - Main Django project
- `speaking_practice/` - Main app for the application logic
- `templates/` - HTML templates
- `static/` - Static files (CSS, JS, images)

## Roles

- **ADMIN**: Full access to all features
- **TEACHER**: Manage lessons and assigned students
- **STUDENT**: Access assigned lessons and practice speaking
- **PARENT**: View their children's progress only

## License

This project is licensed under the MIT License.
