"""
Admin-only content management: one hub page for the whole
Course > Chapter > Lesson > Exercise tree, plus add/edit/delete views.

Follows the project's existing conventions: @login_required with an inline
role check (see views.teacher_create_lesson).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ChapterForm, CourseForm, ExerciseForm, LessonForm
from .models import Chapter, Course, Exercise, Lesson, SpeakingAttempt

MANAGE_MODELS = {
    'course': {
        'model': Course, 'form': CourseForm, 'label': 'Course',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
    },
    'chapter': {
        'model': Chapter, 'form': ChapterForm, 'label': 'Chapter',
        'parent_field': 'course', 'parent_model': Course, 'parent_label': 'Course',
    },
    'lesson': {
        'model': Lesson, 'form': LessonForm, 'label': 'Lesson',
        'parent_field': 'chapter', 'parent_model': Chapter, 'parent_label': 'Chapter',
    },
    'exercise': {
        'model': Exercise, 'form': ExerciseForm, 'label': 'Exercise',
        'parent_field': 'lesson', 'parent_model': Lesson, 'parent_label': 'Lesson',
    },
}


def _admin_or_redirect(request):
    """Return a redirect response when the user is not an admin, else None."""
    if request.user.role != 'admin':
        messages.error(request, 'You do not have permission to manage content.')
        return redirect('dashboard')
    return None


def _get_config(model_name):
    try:
        return MANAGE_MODELS[model_name]
    except KeyError:
        raise Http404(f'Unknown content type: {model_name}')


def _next_order(model, parent_field, parent):
    """Suggest the next order value within the parent scope."""
    if parent_field is None or parent is None:
        return 1
    current_max = model.objects.filter(**{parent_field: parent}).aggregate(
        Max('order'))['order__max']
    return (current_max or 0) + 1


def _cascade_info(obj, model_name):
    """Human-readable list of what else will be deleted with obj."""
    info = []
    if model_name == 'course':
        chapters = obj.chapters.count()
        lessons = Lesson.objects.filter(chapter__course=obj).count()
        exercises = Exercise.objects.filter(lesson__chapter__course=obj).count()
        if chapters:
            info.append(f'{chapters} chapter(s)')
        if lessons:
            info.append(f'{lessons} lesson(s)')
        if exercises:
            info.append(f'{exercises} exercise(s)')
    elif model_name == 'chapter':
        lessons = obj.lessons.count()
        exercises = Exercise.objects.filter(lesson__chapter=obj).count()
        if lessons:
            info.append(f'{lessons} lesson(s)')
        if exercises:
            info.append(f'{exercises} exercise(s)')
    elif model_name == 'lesson':
        exercises = obj.exercises.count()
        attempts = SpeakingAttempt.objects.filter(exercise__lesson=obj).count()
        assigned = obj.assigned_students.count()
        if exercises:
            info.append(f'{exercises} exercise(s)')
        if attempts:
            info.append(f'{attempts} speaking attempt(s)')
        if assigned:
            info.append(f'{assigned} student assignment(s)')
    elif model_name == 'exercise':
        attempts = obj.speaking_attempts.count()
        if attempts:
            info.append(f'{attempts} speaking attempt(s)')
    return info


@login_required
def content_hub(request):
    denied = _admin_or_redirect(request)
    if denied:
        return denied

    tree = []
    courses = Course.objects.prefetch_related(
        'chapters__lessons__exercises').order_by('title')
    for course in courses:
        chapters = []
        lesson_total = 0
        exercise_total = 0
        for chapter in course.chapters.all():
            lessons = []
            for lesson in chapter.lessons.all():
                exercises = list(lesson.exercises.all())
                exercise_total += len(exercises)
                lessons.append({'obj': lesson, 'exercises': exercises})
            lesson_total += len(lessons)
            chapters.append({'obj': chapter, 'lessons': lessons})
        tree.append({
            'obj': course,
            'chapters': chapters,
            'chapter_count': len(chapters),
            'lesson_count': lesson_total,
            'exercise_count': exercise_total,
        })

    return render(request, 'manage_content.html', {'tree': tree})


@login_required
def manage_add(request, model_name):
    cfg = _get_config(model_name)
    denied = _admin_or_redirect(request)
    if denied:
        return denied

    parent = None
    if cfg['parent_field']:
        parent_id = request.GET.get(cfg['parent_field'])
        if parent_id:
            parent = get_object_or_404(cfg['parent_model'], pk=parent_id)

    if request.method == 'POST':
        form = cfg['form'](request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{cfg['label']} '{obj}' created.")
            return redirect('manage_content')
    else:
        initial = {}
        if parent:
            initial[cfg['parent_field']] = parent.pk
            initial['order'] = _next_order(cfg['model'], cfg['parent_field'], parent)
        form = cfg['form'](initial=initial)

    return render(request, 'manage_form.html', {
        'form': form,
        'mode': 'add',
        'label': cfg['label'],
        'parent': parent,
        'parent_label': cfg['parent_label'],
    })


@login_required
def manage_edit(request, model_name, pk):
    cfg = _get_config(model_name)
    denied = _admin_or_redirect(request)
    if denied:
        return denied

    obj = get_object_or_404(cfg['model'], pk=pk)
    if request.method == 'POST':
        form = cfg['form'](request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{cfg['label']} '{obj}' updated.")
            return redirect('manage_content')
    else:
        form = cfg['form'](instance=obj)

    return render(request, 'manage_form.html', {
        'form': form,
        'mode': 'edit',
        'label': cfg['label'],
        'obj': obj,
    })


@login_required
def manage_delete(request, model_name, pk):
    cfg = _get_config(model_name)
    denied = _admin_or_redirect(request)
    if denied:
        return denied

    obj = get_object_or_404(cfg['model'], pk=pk)
    cascade = _cascade_info(obj, model_name)

    if request.method == 'POST':
        name = str(obj)
        obj.delete()
        messages.success(request, f"{cfg['label']} '{name}' deleted.")
        return redirect('manage_content')

    return render(request, 'manage_confirm_delete.html', {
        'obj': obj,
        'label': cfg['label'],
        'cascade': cascade,
    })
