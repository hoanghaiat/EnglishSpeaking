"""
Management Center: one page with tabs for Learning Content, People,
Links & Practice, Classes and Speaking Lessons, plus add/edit/delete
views with modal support.

Access: admins have full access; teachers have scoped access (their own
classes, their students' parent links and lesson assignments).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .changelog import log_change
from .forms import (
    AssignLessonsForm,
    ChapterForm, CourseForm, ExerciseForm, LessonForm,
    ManagedUserCreateForm, ManagedUserEditForm,
    StudentLessonForm, StudentParentForm, StudyClassForm, TeacherStudentForm,
)
from .models import (
    Chapter, Course, Exercise, Lesson, ParentProfile, SpeakingAttempt,
    StudentLesson, StudentParent, StudentProfile, StudyClass,
    TeacherStudent, User,
)

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
    # --- People and Links & Practice (Management Center tabs) ---
    'user': {
        'model': User, 'form': ManagedUserCreateForm,
        'form_edit': ManagedUserEditForm, 'label': 'User',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
    },
    'teacherstudent': {
        'model': TeacherStudent, 'form': TeacherStudentForm,
        'label': 'Teacher\u2013Student link',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
    },
    'studentparent': {
        'model': StudentParent, 'form': StudentParentForm,
        'label': 'Student\u2013Parent link',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
    },
    'studentlesson': {
        'model': StudentLesson, 'form': StudentLessonForm,
        'label': 'Assigned lesson',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
    },
    'speakingattempt': {
        'model': SpeakingAttempt, 'form': None, 'label': 'Speaking attempt',
        'parent_field': None, 'parent_model': None, 'parent_label': None,
        'allow_add': False,
    },
}


def _is_modal(request):
    """True when the client wants a modal fragment instead of a full page."""
    return (request.GET.get('modal') == '1'
            or request.headers.get('x-requested-with') == 'XMLHttpRequest')


def _profile_or_none(user, relation):
    return getattr(user, relation, None)


def _manager_or_redirect(request):
    """Allow admins (full) and teachers (scoped); redirect anyone else."""
    if request.user.role not in ('admin', 'teacher'):
        messages.error(request, 'You do not have permission to manage.')
        return redirect('dashboard')
    return None


def _is_admin(request):
    return request.user.role == 'admin'


def _own_students(teacher_profile):
    return StudentProfile.objects.filter(
        assigned_teachers__teacher=teacher_profile).distinct()


# Generic-CRUD models a teacher may touch (always scoped to own students).
TEACHER_CRUD_MODELS = {'studentparent', 'studentlesson'}


def _crud_permission(request, model_name, obj=None):
    """Return (allowed, teacher_profile_or_None) for the generic CRUD."""
    if _is_admin(request):
        return True, None
    if request.user.role == 'teacher' and model_name in TEACHER_CRUD_MODELS:
        profile = _profile_or_none(request.user, 'teacher_profile')
        if profile is None:
            return False, None
        if obj is not None:
            student = getattr(obj, 'student', None)
            if (student is None
                    or not student.assigned_teachers.filter(
                        teacher=profile).exists()):
                return False, None
        return True, profile
    return False, None


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
    elif model_name == 'user':
        for rel, kind in (('teacher_profile', 'teacher'),
                          ('student_profile', 'student'),
                          ('parent_profile', 'parent')):
            profile = getattr(obj, rel, None)
            if profile is None:
                continue
            info.append(f'{kind} profile')
            if kind == 'teacher':
                if profile.lessons.count():
                    info.append(f'{profile.lessons.count()} taught lesson(s) '
                                '(teacher will be cleared)')
                if profile.assigned_students.count():
                    info.append(f'{profile.assigned_students.count()} '
                                'teacher\u2013student link(s)')
            if kind == 'student':
                if profile.assigned_teachers.count():
                    info.append(f'{profile.assigned_teachers.count()} '
                                'teacher assignment(s)')
                if profile.assigned_lessons.count():
                    info.append(f'{profile.assigned_lessons.count()} '
                                'assigned lesson(s)')
                if profile.speaking_attempts.count():
                    info.append(f'{profile.speaking_attempts.count()} '
                                'speaking attempt(s)')
                if profile.parent_links.count():
                    info.append(f'{profile.parent_links.count()} '
                                'student\u2013parent link(s)')
            if kind == 'parent' and profile.student_links.count():
                info.append(f'{profile.student_links.count()} '
                            'student\u2013parent link(s)')
    return info


def _describe_user(user):
    return f"'{user.username}' ({user.get_role_display()})"


def _actor_name(request):
    return request.user.username


def _log_crud(request, model_name, action, obj, old_role=None):
    """Write a specific, human-readable changelog entry for a CRUD action."""
    actor = request.user
    me = _actor_name(request)

    if model_name == 'user':
        uname = _describe_user(obj)
        teacher = _profile_or_none(obj, 'teacher_profile')
        student = _profile_or_none(obj, 'student_profile')
        if action == 'create':
            log_change(actor, 'user', 'create',
                       f"{me} created user {uname}.",
                       target_user=obj,
                       related_teacher=teacher, related_student=student)
        elif action == 'update':
            if old_role and old_role != obj.role:
                old_label = dict(User.ROLE_CHOICES).get(old_role, old_role)
                log_change(
                    actor, 'role', 'update',
                    f"{me} changed role of {_describe_user(obj)} "
                    f"from {old_label} to {obj.get_role_display()}.",
                    target_user=obj,
                    related_teacher=teacher, related_student=student)
            else:
                log_change(actor, 'user', 'update',
                           f"{me} updated user {uname}.",
                           target_user=obj,
                           related_teacher=teacher, related_student=student)
        elif action == 'delete':
            # obj is already deleted: keep names in the summary text.
            log_change(actor, 'user', 'delete',
                       f"{me} deleted user {uname}.")
        return

    if model_name == 'teacherstudent':
        t, s = obj.teacher.user.username, obj.student.user.username
        if action == 'create':
            log_change(actor, 'relationship', 'link',
                       f"{me} linked teacher '{t}' with student '{s}'.",
                       related_teacher=obj.teacher, related_student=obj.student)
        elif action == 'delete':
            log_change(actor, 'relationship', 'unlink',
                       f"{me} unlinked teacher '{t}' from student '{s}'.")
        return

    if model_name == 'studentparent':
        s, p = obj.student.user.username, obj.parent.user.username
        rel = f" ({obj.relationship_type})" if obj.relationship_type else ""
        if action == 'create':
            log_change(actor, 'relationship', 'link',
                       f"{me} linked student '{s}' with parent '{p}'{rel}.",
                       related_student=obj.student)
        elif action == 'delete':
            log_change(actor, 'relationship', 'unlink',
                       f"{me} unlinked student '{s}' from parent '{p}'{rel}.")
        return

    if model_name == 'studentlesson':
        s = obj.student.user.username
        if action == 'create':
            log_change(actor, 'assignment', 'link',
                       f"{me} assigned lesson '{obj.lesson.title}' "
                       f"to student '{s}'.",
                       related_student=obj.student)
        elif action == 'delete':
            log_change(actor, 'assignment', 'unlink',
                       f"{me} removed lesson '{obj.lesson.title}' "
                       f"from student '{s}'.")
        return

    if model_name == 'speakingattempt' and action == 'delete':
        log_change(actor, 'practice', 'delete',
                   f"{me} deleted a speaking attempt of "
                   f"'{obj.student.user.username}' "
                   f"for exercise '{obj.exercise.title}'.")
        return

    # Learning content.
    label = _get_config(model_name)['label']
    if action == 'create':
        log_change(actor, 'content', 'create',
                   f"{me} created {label.lower()} '{obj}'.")
    elif action == 'update':
        log_change(actor, 'content', 'update',
                   f"{me} updated {label.lower()} '{obj}'.")
    elif action == 'delete':
        log_change(actor, 'content', 'delete',
                   f"{me} deleted {label.lower()} '{obj}'.")


@login_required
def management_center(request):
    """One page with tabs. Admins see everything; teachers see a scoped set."""
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    is_admin = _is_admin(request)
    teacher_profile = None
    if not is_admin:
        teacher_profile = _profile_or_none(request.user, 'teacher_profile')
        if teacher_profile is None:
            messages.error(request,
                             'Teacher profile not found. Please contact an administrator.')
            return redirect('dashboard')

    tab = request.GET.get('tab', '')
    q_learning = request.GET.get('q_learning', '').strip()
    q_people = request.GET.get('q_people', '').strip()
    role_filter = request.GET.get('role', '').strip()
    q_links = request.GET.get('q_links', '').strip()
    q_class = request.GET.get('q_class', '').strip()

    context = {
        'is_admin': is_admin,
        'tab': tab,
        'q_learning': q_learning,
        'q_people': q_people,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
        'q_links': q_links,
        'q_class': q_class,
        'expand_all': bool(q_learning),
        'can_manage_people': is_admin,
        'can_manage_links': True,
    }

    # ---- Learning Content (admin) ----
    if is_admin:
        tree = _build_tree()
        if q_learning:
            tree = _filter_tree(tree, q_learning)
        context['tree'] = tree

    # ---- People ----
    users = User.objects.order_by('username')
    if not is_admin:
        own_students = _own_students(teacher_profile)
        allowed_ids = {request.user.pk}
        allowed_ids.update(
            own_students.values_list('user_id', flat=True))
        allowed_ids.update(
            ParentProfile.objects.filter(
                student_links__student__in=own_students
            ).values_list('user_id', flat=True))
        users = users.filter(pk__in=allowed_ids)
    if role_filter:
        users = users.filter(role=role_filter)
    if q_people:
        users = users.filter(
            Q(username__icontains=q_people)
            | Q(email__icontains=q_people)
            | Q(first_name__icontains=q_people)
            | Q(last_name__icontains=q_people))
    context['users'] = users
    counts = {'total': users.count()}
    for value, label in User.ROLE_CHOICES:
        counts[value] = users.filter(role=value).count()
    context['role_counts'] = counts

    # ---- Links & Practice ----
    if is_admin:
        teacher_students = TeacherStudent.objects.select_related(
            'teacher__user', 'student__user').order_by('-assigned_at')
        student_parents = StudentParent.objects.select_related(
            'student__user', 'parent__user').order_by('-id')
        student_lessons = StudentLesson.objects.select_related(
            'student__user', 'lesson__chapter__course').order_by('-assigned_at')
        recent_attempts = SpeakingAttempt.objects.select_related(
            'student__user', 'exercise__lesson').order_by('-created_at')
    else:
        own_students = _own_students(teacher_profile)
        teacher_students = TeacherStudent.objects.filter(
            teacher=teacher_profile).select_related(
                'teacher__user', 'student__user').order_by('-assigned_at')
        student_parents = StudentParent.objects.filter(
            student__in=own_students).select_related(
                'student__user', 'parent__user').order_by('-id')
        student_lessons = StudentLesson.objects.filter(
            student__in=own_students).select_related(
                'student__user', 'lesson__chapter__course').order_by(
                    '-assigned_at')
        recent_attempts = SpeakingAttempt.objects.filter(
            student__in=own_students).select_related(
                'student__user', 'exercise__lesson').order_by('-created_at')
    if q_links:
        teacher_students = teacher_students.filter(
            Q(teacher__user__username__icontains=q_links)
            | Q(student__user__username__icontains=q_links))
        student_parents = student_parents.filter(
            Q(student__user__username__icontains=q_links)
            | Q(parent__user__username__icontains=q_links))
        student_lessons = student_lessons.filter(
            Q(student__user__username__icontains=q_links)
            | Q(lesson__title__icontains=q_links))
        recent_attempts = recent_attempts.filter(
            Q(student__user__username__icontains=q_links)
            | Q(exercise__title__icontains=q_links))
    context.update(
        teacher_students=teacher_students[:200],
        student_parents=student_parents[:200],
        student_lessons=student_lessons[:200],
        recent_attempts=recent_attempts[:50],
    )

    # ---- Classes ----
    if is_admin:
        classes = StudyClass.objects.select_related(
            'teacher__user').prefetch_related('students__user')
    else:
        classes = StudyClass.objects.filter(
            teacher=teacher_profile).prefetch_related('students__user')
    if q_class:
        classes = classes.filter(
            Q(name__icontains=q_class)
            | Q(teacher__user__username__icontains=q_class))
    context['study_classes'] = classes.order_by('name')

    # ---- Speaking Lessons (admin) ----
    if is_admin:
        context['all_lessons'] = Lesson.objects.select_related(
            'teacher__user', 'chapter__course').order_by(
                'chapter__course__title', 'chapter__order', 'order')

    return render(request, 'manage_center.html', context)


def _build_tree():
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
    return tree


def _recount(node):
    chapters = node['chapters']
    lesson_total = sum(len(c['lessons']) for c in chapters)
    exercise_total = sum(len(l['exercises'])
                         for c in chapters for l in c['lessons'])
    node['chapter_count'] = len(chapters)
    node['lesson_count'] = lesson_total
    node['exercise_count'] = exercise_total
    return node


def _filter_tree(tree, query):
    """Keep only branches matching the query (case-insensitive)."""
    ql = query.lower()
    result = []
    for node in tree:
        chapters = []
        for cnode in node['chapters']:
            lessons = []
            for lnode in cnode['lessons']:
                exercises = [e for e in lnode['exercises']
                             if ql in e.title.lower()]
                if ql in lnode['obj'].title.lower() or exercises:
                    lessons.append({'obj': lnode['obj'],
                                    'exercises': exercises})
            if ql in cnode['obj'].title.lower() or lessons:
                chapters.append({'obj': cnode['obj'], 'lessons': lessons})
        if ql in node['obj'].title.lower() or chapters:
            result.append(_recount({'obj': node['obj'], 'chapters': chapters}))
    return result


@login_required
def manage_add(request, model_name):
    cfg = _get_config(model_name)
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    allowed, teacher_profile = _crud_permission(request, model_name)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')
    if not cfg.get('allow_add', True):
        raise Http404(f'Cannot add: {model_name}')

    form_kwargs = {}
    if teacher_profile is not None:
        form_kwargs['teacher_profile'] = teacher_profile

    parent = None
    if cfg['parent_field']:
        parent_id = request.GET.get(cfg['parent_field'])
        if parent_id:
            parent = get_object_or_404(cfg['parent_model'], pk=parent_id)

    if request.method == 'POST':
        form = cfg['form'](request.POST, request.FILES, **form_kwargs)
        if form.is_valid():
            if teacher_profile is not None:
                student = form.cleaned_data.get('student')
                if (student is None or not student.assigned_teachers.filter(
                        teacher=teacher_profile).exists()):
                    form.add_error(
                        None, 'You can only manage your own students.')
            if not form.errors:
                obj = form.save()
                messages.success(request, f"{cfg['label']} '{obj}' created.")
                _log_crud(request, model_name, 'create', obj)
                if _is_modal(request):
                    return JsonResponse({'ok': True})
                return redirect('manage_center')
    else:
        initial = {}
        if parent:
            initial[cfg['parent_field']] = parent.pk
            initial['order'] = _next_order(cfg['model'], cfg['parent_field'], parent)
        form = cfg['form'](initial=initial, **form_kwargs)

    template = 'manage_form_modal.html' if _is_modal(request) else 'manage_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'add',
        'label': cfg['label'],
        'parent': parent,
        'parent_label': cfg['parent_label'],
    })


@login_required
def manage_edit(request, model_name, pk):
    cfg = _get_config(model_name)
    denied = _manager_or_redirect(request)
    if denied:
        return denied

    obj = get_object_or_404(cfg['model'], pk=pk)
    allowed, teacher_profile = _crud_permission(request, model_name, obj)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')

    form_kwargs = {}
    if teacher_profile is not None:
        form_kwargs['teacher_profile'] = teacher_profile
    form_class = cfg.get('form_edit') or cfg['form']
    # Capture before the bound form mutates obj in place during validation.
    old_role = obj.role if model_name == 'user' else None
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=obj,
                          **form_kwargs)
        if form.is_valid():
            if (model_name == 'user' and obj == request.user
                    and (form.cleaned_data.get('role') != 'admin'
                         or not form.cleaned_data.get('is_active'))):
                form.add_error(
                    None, 'You cannot remove your own admin access.')
            else:
                form.save()
                messages.success(request, f"{cfg['label']} '{obj}' updated.")
                _log_crud(request, model_name, 'update', obj,
                          old_role=old_role)
                if _is_modal(request):
                    return JsonResponse({'ok': True})
                return redirect('manage_center')
    else:
        form = form_class(instance=obj, **form_kwargs)

    template = 'manage_form_modal.html' if _is_modal(request) else 'manage_form.html'
    return render(request, template, {
        'form': form,
        'mode': 'edit',
        'label': cfg['label'],
        'obj': obj,
    })


@login_required
def manage_delete(request, model_name, pk):
    cfg = _get_config(model_name)
    denied = _manager_or_redirect(request)
    if denied:
        return denied

    obj = get_object_or_404(cfg['model'], pk=pk)
    allowed, _teacher_profile = _crud_permission(request, model_name, obj)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')
    cascade = _cascade_info(obj, model_name)

    if model_name == 'user' and obj == request.user:
        messages.error(request, 'You cannot delete your own account.')
        if _is_modal(request):
            return render(request, 'manage_delete_modal.html', {
                'obj': obj, 'label': cfg['label'], 'cascade': cascade,
                'error': 'You cannot delete your own account.',
            })
        return redirect('manage_center')

    if request.method == 'POST':
        name = str(obj)
        _log_crud(request, model_name, 'delete', obj)
        obj.delete()
        messages.success(request, f"{cfg['label']} '{name}' deleted.")
        if _is_modal(request):
            return JsonResponse({'ok': True})
        return redirect('manage_center')

    template = ('manage_delete_modal.html'
                if _is_modal(request) else 'manage_confirm_delete.html')
    return render(request, template, {
        'obj': obj,
        'label': cfg['label'],
        'cascade': cascade,
    })


# ---------------------------------------------------------------------------
# Study classes
# ---------------------------------------------------------------------------

def _class_permission(request, obj=None):
    """Return (allowed, teacher_profile_or_None, is_admin) for classes."""
    if _is_admin(request):
        return True, None, True
    profile = _profile_or_none(request.user, 'teacher_profile')
    if profile is None:
        return False, None, False
    if obj is not None and obj.teacher_id != profile.pk:
        return False, None, False
    return True, profile, False


@login_required
def class_add(request):
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    allowed, teacher_profile, is_admin = _class_permission(request)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')

    if request.method == 'POST':
        form = StudyClassForm(request.POST, teacher_profile=teacher_profile,
                              is_admin=is_admin)
        if is_admin:
            # The 'teacher' field is added dynamically (not in Meta.fields),
            # so bind it to the instance early for unique_together validation.
            try:
                form.instance.teacher_id = int(request.POST.get('teacher') or 0) or None
            except (TypeError, ValueError):
                pass
        else:
            form.instance.teacher = teacher_profile
        if form.is_valid():
            obj = form.save()
            n = obj.students.count()
            log_change(
                request.user, 'class', 'create',
                f"{request.user.username} created class '{obj.name}' "
                f"with {n} student(s).",
                related_teacher=obj.teacher)
            messages.success(request, f"Class '{obj.name}' created.")
            if _is_modal(request):
                return JsonResponse({'ok': True})
            return redirect('manage_center')
    else:
        form = StudyClassForm(teacher_profile=teacher_profile,
                              is_admin=is_admin)

    template = 'manage_form_modal.html' if _is_modal(request) else 'manage_form.html'
    return render(request, template, {
        'form': form, 'mode': 'add', 'label': 'Class',
        'parent': None, 'parent_label': None,
    })


@login_required
def class_edit(request, pk):
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    obj = get_object_or_404(StudyClass, pk=pk)
    allowed, teacher_profile, is_admin = _class_permission(request, obj)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')

    if request.method == 'POST':
        form = StudyClassForm(request.POST, instance=obj,
                              teacher_profile=teacher_profile,
                              is_admin=is_admin)
        if is_admin:
            try:
                form.instance.teacher_id = int(request.POST.get('teacher') or 0) or None
            except (TypeError, ValueError):
                pass
        if form.is_valid():
            form.save()
            n = obj.students.count()
            log_change(
                request.user, 'class', 'update',
                f"{request.user.username} updated class '{obj.name}' "
                f"({n} student(s)).",
                related_teacher=obj.teacher)
            messages.success(request, f"Class '{obj.name}' updated.")
            if _is_modal(request):
                return JsonResponse({'ok': True})
            return redirect('manage_center')
    else:
        form = StudyClassForm(instance=obj, teacher_profile=teacher_profile,
                              is_admin=is_admin)

    template = 'manage_form_modal.html' if _is_modal(request) else 'manage_form.html'
    return render(request, template, {
        'form': form, 'mode': 'edit', 'label': 'Class', 'obj': obj,
    })


@login_required
def class_delete(request, pk):
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    obj = get_object_or_404(StudyClass, pk=pk)
    allowed, _tp, _is_admin = _class_permission(request, obj)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')

    n = obj.students.count()
    cascade = ([f'{n} student(s) will be unassigned '
                '(the students themselves are kept)'] if n else [])
    if request.method == 'POST':
        name = obj.name
        log_change(request.user, 'class', 'delete',
                   f"{request.user.username} deleted class '{name}'.",
                   related_teacher=obj.teacher)
        obj.delete()
        messages.success(request, f"Class '{name}' deleted.")
        if _is_modal(request):
            return JsonResponse({'ok': True})
        return redirect('manage_center')

    template = ('manage_delete_modal.html'
                if _is_modal(request) else 'manage_confirm_delete.html')
    return render(request, template, {
        'obj': obj, 'label': 'Class', 'cascade': cascade,
    })


# ---------------------------------------------------------------------------
# Assign lessons (by class or by individual students)
# ---------------------------------------------------------------------------

@login_required
def assign_lessons(request):
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    is_admin = _is_admin(request)
    teacher_profile = None
    if not is_admin:
        teacher_profile = _profile_or_none(request.user, 'teacher_profile')
        if teacher_profile is None:
            messages.error(request,
                             'Teacher profile not found. Please contact an administrator.')
            return redirect('dashboard')

    if request.method == 'POST':
        form = AssignLessonsForm(request.POST, teacher_profile=teacher_profile,
                                 is_admin=is_admin)
        if form.is_valid():
            lesson = form.cleaned_data['lesson']
            if form.cleaned_data['target'] == 'class':
                study_class = form.cleaned_data['study_class']
                students = list(study_class.students.all())
                scope = f"class '{study_class.name}'"
            else:
                students = list(form.cleaned_data['students'])
                scope = f"{len(students)} selected student(s)"
            created = 0
            for student in students:
                _, was_created = StudentLesson.objects.get_or_create(
                    student=student, lesson=lesson)
                created += was_created
            log_change(
                request.user, 'assignment', 'create',
                f"{request.user.username} assigned lesson "
                f"'{lesson.title}' to {scope} "
                f"({created} new assignment(s)).",
                related_teacher=(None if is_admin
                                 else teacher_profile))
            messages.success(
                request,
                f"Lesson '{lesson.title}' assigned to {scope} "
                f"({created} new).")
            if _is_modal(request):
                return JsonResponse({'ok': True})
            return redirect('manage_center')
    else:
        form = AssignLessonsForm(teacher_profile=teacher_profile,
                                 is_admin=is_admin)

    template = 'manage_form_modal.html' if _is_modal(request) else 'manage_form.html'
    return render(request, template, {
        'form': form, 'mode': 'add', 'label': 'Lesson assignment',
        'parent': None, 'parent_label': None,
    })


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------

@login_required
def changelog_list(request):
    from .changelog import changelog_for
    from .models import ChangeLog
    if request.user.role not in ('admin', 'teacher'):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    category = request.GET.get('category', '').strip()
    entries = changelog_for(request.user)
    valid = {key for key, _label in ChangeLog.CATEGORY_CHOICES}
    if category in valid:
        entries = entries.filter(category=category)
    else:
        category = ''
    return render(request, 'changelog_list.html', {
        'entries': entries[:200],
        'category': category,
        'categories': ChangeLog.CATEGORY_CHOICES,
    })


@login_required
def class_remove_student(request, pk, student_pk):
    """Quick-remove one student from a class ("move out")."""
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    obj = get_object_or_404(StudyClass, pk=pk)
    allowed, _tp, _is_admin = _class_permission(request, obj)
    if not allowed:
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')
    student = get_object_or_404(StudentProfile, pk=student_pk)
    if request.method == 'POST' and obj.students.filter(pk=student.pk).exists():
        obj.students.remove(student)
        log_change(request.user, 'class', 'update',
                   f"{request.user.username} removed student "
                   f"'{student.user.username}' from class '{obj.name}'.",
                   related_teacher=obj.teacher,
                   related_student=student)
        messages.success(
            request,
            f"Removed '{student.user.username}' from class '{obj.name}'.")
    redirect_to = request.POST.get('next') or request.GET.get('next')
    if redirect_to and redirect_to.startswith('/manage/'):
        return redirect(redirect_to)
    return redirect('manage_center')


@login_required
def lesson_preview(request, pk):
    """Read-only lesson preview shown in a modal (stays on the page)."""
    denied = _manager_or_redirect(request)
    if denied:
        return denied
    if not _is_admin(request):
        messages.error(request, 'You do not have permission for this action.')
        return redirect('manage_center')
    lesson = get_object_or_404(
        Lesson.objects.select_related('teacher__user', 'chapter__course'),
        pk=pk)
    exercises = lesson.exercises.order_by('order')
    if _is_modal(request):
        return render(request, 'manage_lesson_preview.html', {
            'lesson': lesson, 'exercises': exercises,
        })
    return redirect('manage_center')
