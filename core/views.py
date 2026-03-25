from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import get_template
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from django.conf import settings
import os
import io
import json
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User

from .models import (
    Student, Teacher, Course, Department,
    Enrollment, Attendance, Exam, Mark, Report, Subject
)

# =========================
# AUTH
# =========================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "❌ Invalid username or password")
    return render(request, 'login.html')


def logout_view(request):
    # POST aur GET dono se logout karo — button click karne pe kaam kare
    logout(request)
    return redirect('login')


# =========================
# DASHBOARD
# =========================
@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        monthly_data = (
            Student.objects
            .annotate(month=TruncMonth('admission_date'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        growth_labels = [
            entry['month'].strftime('%b %Y')
            for entry in monthly_data if entry['month']
        ]
        growth_data = [
            entry['count']
            for entry in monthly_data if entry['month']
        ]

        dept_data = (
            Department.objects
            .annotate(student_count=Count('student'))
            .values('name', 'student_count')
        )
        dept_labels = [d['name'] for d in dept_data]
        dept_counts = [d['student_count'] for d in dept_data]

        recent_students = Student.objects.select_related('user').order_by('-id')[:5]
        recent_teachers = Teacher.objects.select_related('user').order_by('-id')[:5]
        recent_courses  = Course.objects.order_by('-id')[:5]

        recent_activity = []
        for s in recent_students:
            recent_activity.append({
                'type': 'student',
                'icon': 'fas fa-user-graduate',
                'color': '#667eea',
                'text': f"{s.user.get_full_name() or s.user.username} enrolled",
                'sub': f"Roll No: {s.roll_number}",
                'date': s.admission_date,
            })
        for t in recent_teachers:
            recent_activity.append({
                'type': 'teacher',
                'icon': 'fas fa-chalkboard-teacher',
                'color': '#0d9488',
                'text': f"{t.user.get_full_name() or t.user.username} joined as Teacher",
                'sub': f"Employee ID: {t.employee_id}",
                'date': t.joining_date,
            })
        for c in recent_courses:
            recent_activity.append({
                'type': 'course',
                'icon': 'fas fa-book-open',
                'color': '#f59e0b',
                'text': f"Course '{c.name}' added",
                'sub': f"Code: {c.code}",
                'date': None,
            })

        recent_activity.sort(
            key=lambda x: x['date'] if x['date'] else __import__('datetime').date.min,
            reverse=True
        )
        recent_activity = recent_activity[:8]

        return render(request, 'dashboard.html', {
            'role':              'admin',
            'total_students':    Student.objects.count(),
            'total_teachers':    Teacher.objects.count(),
            'total_courses':     Course.objects.count(),
            'total_departments': Department.objects.count(),
            'growth_labels':     json.dumps(growth_labels),
            'growth_data':       json.dumps(growth_data),
            'dept_labels':       json.dumps(dept_labels),
            'dept_counts':       json.dumps(dept_counts),
            'recent_activity':   recent_activity,
        })

    if Teacher.objects.filter(user=user).exists():
        teacher = Teacher.objects.get(user=user)
        students = Student.objects.filter(
            enrollments__course__subjects__teacher=teacher
        ).distinct()

        attendance = Attendance.objects.filter(marked_by=teacher)
        attendance_count = attendance.count()
        present_count = attendance.filter(status='present').count()
        absent_count  = attendance.filter(status='absent').count()
        present_percent = round((present_count / attendance_count) * 100, 1) if attendance_count > 0 else 0
        absent_percent  = round((absent_count  / attendance_count) * 100, 1) if attendance_count > 0 else 0

        top_students = (
            Mark.objects
            .filter(exam__subject__teacher=teacher)
            .select_related('student__user', 'exam__subject')
            .order_by('-marks_obtained')
        )
        seen_students = set()
        leaderboard = []
        for m in top_students:
            if m.student_id not in seen_students:
                leaderboard.append(m)
                seen_students.add(m.student_id)
            if len(leaderboard) == 5:
                break

        return render(request, 'dashboard.html', {
            'role': 'teacher',
            'teacher': teacher,
            'total_students': students.count(),
            'attendance_count': attendance_count,
            'present_count': present_count,
            'absent_count': absent_count,
            'present_percent': present_percent,
            'absent_percent': absent_percent,
            'recent_attendance': attendance.order_by('-date')[:5],
            'top_students': leaderboard,
        })

    if Student.objects.filter(user=user).exists():
        student = Student.objects.get(user=user)
        total_att   = Attendance.objects.filter(student=student).count()
        present_att = Attendance.objects.filter(student=student, status='present').count()
        absent_att  = total_att - present_att
        attendance_percentage = (present_att / total_att * 100) if total_att > 0 else 0

        marks_qs   = Mark.objects.filter(student=student).select_related('exam__subject')
        subjects   = []
        marks_data = []
        for m in marks_qs:
            subjects.append(m.exam.subject.name)
            marks_data.append(float(m.marks_obtained))

        # ✅ BUG FIX 7: avg_percentage ab properly calculate ho raha hai
        avg_percentage = 0
        if marks_qs.exists():
            total_pct = sum(
                (m.marks_obtained / m.exam.max_marks * 100)
                for m in marks_qs if m.exam.max_marks > 0
            )
            avg_percentage = round(total_pct / marks_qs.count(), 1)

        return render(request, 'dashboard.html', {
            'role': 'student',
            'student': student,
            'attendance_percentage': round(attendance_percentage, 2),
            'present_att': present_att,
            'absent_att': absent_att,
            'subjects': json.dumps(subjects),
            'marks': json.dumps(marks_data),
            'has_marks': len(marks_data) > 0,
            'avg_percentage': avg_percentage,
        })

    return redirect('login')


# =========================
# STUDENTS
# =========================
@login_required
def students_list(request):
    if not (request.user.is_superuser or Teacher.objects.filter(user=request.user).exists()):
        return redirect('dashboard')

    students    = Student.objects.select_related('user', 'department')
    departments = Department.objects.all()
    courses     = Course.objects.all()
    teachers    = Teacher.objects.select_related('user')

    search = request.GET.get('search')
    if search:
        students = students.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(roll_number__icontains=search)
        )

    dept_id = request.GET.get('department')
    if dept_id:
        students = students.filter(department__id=dept_id)

    return render(request, 'students/list.html', {
        'students':    students,
        'departments': departments,
        'courses':     courses,
        'teachers':    teachers,
        'subjects':    Subject.objects.select_related('course', 'teacher').all(),
        'exams':       Exam.objects.select_related('subject').all(),
    })


@login_required
def student_detail(request, pk):
    student    = get_object_or_404(Student, pk=pk)
    marks      = Mark.objects.filter(student=student).select_related('exam__subject')
    attendance = Attendance.objects.filter(student=student)

    total_classes = attendance.count()
    present_count = attendance.filter(status='present').count()
    absent_count  = total_classes - present_count
    percentage    = (present_count / total_classes * 100) if total_classes > 0 else 0

    return render(request, 'students/detail.html', {
        'student': student,
        'marks': marks,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_classes': total_classes,
        'attendance_percentage': round(percentage, 2),
    })


@login_required
def student_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        username   = request.POST.get('username')
        password   = request.POST.get('password')
        first_name  = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()
        email       = request.POST.get('email', '')

        # Middle name ko first name ke saath join karo
        full_first = f"{first_name} {middle_name}".strip() if middle_name else first_name

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Username already exists!')
            return redirect('students_list')

        user = User.objects.create_user(
            username=username, password=password,
            first_name=full_first, last_name=last_name, email=email
        )

        dept_id        = request.POST.get('department')
        roll_number    = request.POST.get('roll_number')
        admission_date = request.POST.get('admission_date')
        phone          = request.POST.get('phone', '')
        parent_name    = request.POST.get('parent_name', '')
        parent_phone   = request.POST.get('parent_phone', '')

        # ✅ BUG FIX: try/except so bad dept_id doesn't crash
        try:
            dept = Department.objects.get(id=dept_id) if dept_id else None
        except Department.DoesNotExist:
            dept = None

        student = Student.objects.create(
            user=user,
            roll_number=roll_number,
            department=dept,
            admission_date=admission_date,
            phone=phone,
            parent_name=parent_name,
            parent_phone=parent_phone,
        )

        if 'profile_image' in request.FILES:
            student.profile_image = request.FILES['profile_image']
            student.save()

        course_id = request.POST.get('course')
        if course_id:
            try:
                Enrollment.objects.create(
                    student=student,
                    course=Course.objects.get(id=course_id)
                )
            except Course.DoesNotExist:
                pass

        messages.success(request, f'✅ Student {first_name} {last_name} added successfully!')
    return redirect('students_list')


@login_required
def student_edit(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        user        = student.user
        first_name  = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()

        # Middle name ko first name ke saath join karo
        user.first_name = f"{first_name} {middle_name}".strip() if middle_name else first_name
        user.last_name  = last_name
        user.email      = request.POST.get('email', '')
        user.save()

        dept_id              = request.POST.get('department')
        student.roll_number  = request.POST.get('roll_number', student.roll_number)
        student.phone        = request.POST.get('phone', '')
        student.parent_name  = request.POST.get('parent_name', '')
        student.parent_phone = request.POST.get('parent_phone', '')

        try:
            student.department = Department.objects.get(id=dept_id) if dept_id else student.department
        except Department.DoesNotExist:
            pass

        if 'profile_image' in request.FILES:
            student.profile_image = request.FILES['profile_image']

        student.save()
        messages.success(request, '✅ Student updated successfully!')
    return redirect('students_list')


@login_required
def student_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        user = student.user
        student.delete()
        user.delete()
        messages.success(request, '✅ Student deleted successfully!')
    return redirect('students_list')


# =========================
# TEACHERS
# =========================
@login_required
def teacher_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        username   = request.POST.get('username')
        password   = request.POST.get('password')
        first_name  = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()
        email       = request.POST.get('email', '')

        # Middle name ko first name ke saath join karo
        full_first = f"{first_name} {middle_name}".strip() if middle_name else first_name

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Username already exists!')
            return redirect('students_list')

        user = User.objects.create_user(
            username=username, password=password,
            first_name=full_first, last_name=last_name, email=email
        )

        dept_id      = request.POST.get('department')
        employee_id  = request.POST.get('employee_id')
        joining_date = request.POST.get('joining_date')
        phone        = request.POST.get('phone', '')

        try:
            dept = Department.objects.get(id=dept_id) if dept_id else None
        except Department.DoesNotExist:
            dept = None

        teacher = Teacher.objects.create(
            user=user,
            employee_id=employee_id,
            department=dept,
            joining_date=joining_date,
            phone=phone,
        )

        if 'profile_image' in request.FILES:
            teacher.profile_image = request.FILES['profile_image']
            teacher.save()

        messages.success(request, f'✅ Teacher {first_name} {last_name} added successfully!')
    return redirect('students_list')


@login_required
def teacher_edit(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    teacher = get_object_or_404(Teacher, pk=pk)

    if request.method == 'POST':
        user        = teacher.user
        first_name  = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()

        # Middle name ko first name ke saath join karo
        user.first_name = f"{first_name} {middle_name}".strip() if middle_name else first_name
        user.last_name  = last_name
        user.email      = request.POST.get('email', '')
        user.save()

        dept_id            = request.POST.get('department')
        teacher.employee_id = request.POST.get('employee_id', teacher.employee_id)
        teacher.phone      = request.POST.get('phone', '')

        try:
            teacher.department = Department.objects.get(id=dept_id) if dept_id else teacher.department
        except Department.DoesNotExist:
            pass

        if 'profile_image' in request.FILES:
            teacher.profile_image = request.FILES['profile_image']

        teacher.save()
        messages.success(request, '✅ Teacher updated successfully!')
    return redirect('students_list')


@login_required
def teacher_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        user = teacher.user
        teacher.delete()
        user.delete()
        messages.success(request, '✅ Teacher deleted successfully!')
    return redirect('students_list')


# =========================
# DEPARTMENT
# =========================
@login_required
def department_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        desc = request.POST.get('description', '')
        if Department.objects.filter(code=code).exists():
            messages.error(request, '❌ Department code already exists!')
        else:
            Department.objects.create(name=name, code=code, description=desc)
            messages.success(request, f'✅ Department {name} added!')
    return redirect('students_list')


@login_required
def department_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    dept = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        dept.delete()
        messages.success(request, '✅ Department deleted!')
    return redirect('students_list')


# =========================
# COURSE
# =========================
@login_required
def course_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        name    = request.POST.get('name')
        code    = request.POST.get('code')
        dept_id = request.POST.get('department')
        credits = request.POST.get('credits', 3)
        if Course.objects.filter(code=code).exists():
            messages.error(request, '❌ Course code already exists!')
        else:
            try:
                dept = Department.objects.get(id=dept_id) if dept_id else None
            except Department.DoesNotExist:
                dept = None
            Course.objects.create(name=name, code=code, credits=credits, department=dept)
            messages.success(request, f'✅ Course {name} added!')
    return redirect('students_list')


@login_required
def course_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, '✅ Course deleted!')
    return redirect('students_list')


# =========================
# SUBJECT
# =========================
@login_required
def subject_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        name       = request.POST.get('name')
        code       = request.POST.get('code')
        course_id  = request.POST.get('course')
        teacher_id = request.POST.get('teacher')
        max_marks  = request.POST.get('max_marks', 100)

        if Subject.objects.filter(code=code).exists():
            messages.error(request, '❌ Subject code already exists!')
        else:
            try:
                course  = Course.objects.get(id=course_id) if course_id else None
                teacher = Teacher.objects.get(id=teacher_id) if teacher_id else None
            except (Course.DoesNotExist, Teacher.DoesNotExist):
                course  = None
                teacher = None
            Subject.objects.create(name=name, code=code, course=course, teacher=teacher, max_marks=max_marks)
            messages.success(request, f'✅ Subject {name} added!')
    return redirect('students_list')


@login_required
def subject_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, '✅ Subject deleted!')
    return redirect('students_list')


# =========================
# ATTENDANCE
# =========================
@login_required
def attendance_list(request):
    user = request.user

    if Student.objects.filter(user=user).exists():
        student     = Student.objects.get(user=user)
        attendances = Attendance.objects.filter(student=student).order_by('-date')
        total   = attendances.count()
        present = attendances.filter(status='present').count()
        absent  = attendances.filter(status='absent').count()
        late    = attendances.filter(status='late').count()
        percentage = round((present / total * 100), 2) if total > 0 else 0
        return render(request, 'attendance/student_list.html', {
            'attendances': attendances,
            'present': present, 'absent': absent,
            'late': late, 'percentage': percentage,
        })

    if Teacher.objects.filter(user=user).exists():
        teacher  = Teacher.objects.get(user=user)
        subjects = teacher.subjects.all()
        return render(request, 'attendance/teacher_list.html', {'subjects': subjects})

    attendances = Attendance.objects.all()
    return render(request, 'attendance/admin_list.html', {'attendances': attendances})


@login_required
def mark_attendance(request, subject_id):
    teacher  = get_object_or_404(Teacher, user=request.user)
    subject  = get_object_or_404(Subject, pk=subject_id)
    students = Student.objects.filter(
        enrollments__course=subject.course,
        enrollments__is_active=True
    )

    if request.method == 'POST':
        date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d').date()
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=student, subject=subject, date=date,
                    defaults={'status': status, 'marked_by': teacher}
                )
        messages.success(request, '✅ Attendance saved successfully!')
        return redirect('attendance_list')

    return render(request, 'attendance/mark.html', {
        'subject': subject, 'students': students,
        'today': datetime.now().date()
    })


# =========================
# MARKS
# =========================
@login_required
def marks_list(request):
    user = request.user

    if Student.objects.filter(user=user).exists():
        student = Student.objects.get(user=user)
        marks   = Mark.objects.filter(student=student).select_related('exam', 'exam__subject')

        # ✅ BUG FIX 7: avg_percentage marks page pe bhi calculate karo
        avg_percentage = 0
        if marks.exists():
            total_pct = sum(
                (m.marks_obtained / m.exam.max_marks * 100)
                for m in marks if m.exam.max_marks > 0
            )
            avg_percentage = round(total_pct / marks.count(), 1)

        return render(request, 'marks/student_list.html', {
            'marks': marks,
            'avg_percentage': avg_percentage,
        })

    if Teacher.objects.filter(user=user).exists():
        teacher  = Teacher.objects.get(user=user)
        exams    = Exam.objects.filter(subject__teacher=teacher).select_related('subject')
        subjects = teacher.subjects.all()
        return render(request, 'marks/teacher_list.html', {
            'exams': exams, 'subjects': subjects,
        })

    marks = Mark.objects.all()
    return render(request, 'marks/admin_list.html', {'marks': marks})


@login_required
def enter_marks(request, exam_id):
    teacher  = get_object_or_404(Teacher, user=request.user)
    exam     = get_object_or_404(Exam, pk=exam_id)
    students = Student.objects.filter(
        enrollments__course=exam.subject.course,
        enrollments__is_active=True
    )

    if request.method == 'POST':
        for student in students:
            ci_1    = request.POST.get(f'ci1_{student.id}')
            ci_2    = request.POST.get(f'ci2_{student.id}')
            ci_3    = request.POST.get(f'ci3_{student.id}')
            remarks = request.POST.get(f'remarks_{student.id}', '')

            ci_1 = float(ci_1) if ci_1 else 0
            ci_2 = float(ci_2) if ci_2 else 0
            ci_3 = float(ci_3) if ci_3 else 0

            # ✅ BUG FIX 5: max_marks validation
            total_marks = ci_1 + ci_2 + ci_3
            if exam.max_marks > 0 and total_marks > exam.max_marks:
                messages.error(
                    request,
                    f'❌ {student.user.get_full_name()} ke marks ({total_marks}) max marks ({exam.max_marks}) se zyada hain!'
                )
                existing_marks = {m.student_id: m for m in Mark.objects.filter(exam=exam)}
                return render(request, 'marks/enter.html', {
                    'exam': exam, 'students': students,
                    'existing_marks': existing_marks,
                })

            mark_obj, _ = Mark.objects.update_or_create(
                student=student,
                exam=exam,
                defaults={
                    'ci_1': ci_1,
                    'ci_2': ci_2,
                    'ci_3': ci_3,
                    'remarks': remarks,
                    'entered_by': teacher
                }
            )
            # ✅ BUG FIX 4: model ka calculate_total() use karo
            mark_obj.marks_obtained = mark_obj.calculate_total()
            mark_obj.save()

        messages.success(request, '✅ Marks saved successfully!')
        return redirect('marks_list')

    existing_marks = {m.student_id: m for m in Mark.objects.filter(exam=exam)}
    return render(request, 'marks/enter.html', {
        'exam': exam, 'students': students, 'existing_marks': existing_marks,
    })


# =========================
# EXAM
# =========================
@login_required
def exam_add(request):
    if not request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        name      = request.POST.get('name')
        exam_type = request.POST.get('exam_type')
        date      = request.POST.get('date')
        max_marks = request.POST.get('max_marks', 100)
        duration  = request.POST.get('duration_minutes', None)

        # ✅ NEW: Multiple subjects — getlist se saare selected subjects aate hain
        subject_ids = request.POST.getlist('subjects')

        if not subject_ids:
            messages.error(request, '❌ Please select at least one subject!')
            return redirect('students_list')

        created_count = 0
        for subject_id in subject_ids:
            try:
                subject = Subject.objects.get(id=subject_id)
                Exam.objects.create(
                    name=name,
                    exam_type=exam_type,
                    subject=subject,
                    date=date,
                    max_marks=max_marks,
                    duration_minutes=duration if duration else None,
                )
                created_count += 1
            except Subject.DoesNotExist:
                pass

        if created_count == 1:
            messages.success(request, f'✅ Exam "{name}" added successfully!')
        elif created_count > 1:
            messages.success(request, f'✅ Exam "{name}" added for {created_count} subjects!')

    return redirect('students_list')


@login_required
def exam_delete(request, pk):
    if not request.user.is_superuser:
        return redirect('dashboard')

    exam = get_object_or_404(Exam, pk=pk)
    if request.method == 'POST':
        exam.delete()
        messages.success(request, '✅ Exam deleted!')

    # ✅ BUG FIX 2: marks_list pe redirect karo
    return redirect('marks_list')


# =========================
# REPORTS + PDF
# =========================
@login_required
def reports(request):
    if Student.objects.filter(user=request.user).exists():
        student = Student.objects.get(user=request.user)
        reports = Report.objects.filter(student=student)
        return render(request, 'reports/student.html', {'reports': reports})

    # Admin/Teacher — sab students ke reports dikhao
    reports = Report.objects.all().select_related('student__user', 'course')
    students = Student.objects.select_related('user', 'department').all()
    return render(request, 'reports/student.html', {
        'reports': reports,
        'students': students,
    })


@login_required
def generate_all_reports(request):
    """
    Admin ke liye — ek click mein sab students ke reports generate karo.
    Har student ke marks aur attendance se automatically calculate hota hai.
    """
    if not request.user.is_superuser:
        messages.error(request, '❌ Only admin can generate reports!')
        return redirect('reports')

    if request.method != 'POST':
        return redirect('reports')

    students = Student.objects.all()
    generated = 0
    updated   = 0
    skipped   = 0

    current_year  = datetime.now().year
    academic_year = f"{current_year - 1}-{current_year}"
    semester      = request.POST.get('semester', '1')

    for student in students:
        # Student ke marks fetch karo
        marks = Mark.objects.filter(student=student).select_related('exam', 'exam__subject__course')

        if not marks.exists():
            skipped += 1
            continue

        # Course — enrollment se lo
        enrollment = student.enrollments.filter(is_active=True).first()
        if not enrollment:
            skipped += 1
            continue

        course = enrollment.course

        # Total aur obtained marks calculate karo
        total_marks    = sum(m.exam.max_marks for m in marks if m.exam.max_marks)
        obtained_marks = sum(m.marks_obtained for m in marks)
        percentage     = round((obtained_marks / total_marks * 100), 2) if total_marks > 0 else 0

        # Grade calculate karo
        if percentage >= 90:   grade = 'A+'
        elif percentage >= 80: grade = 'A'
        elif percentage >= 70: grade = 'B+'
        elif percentage >= 60: grade = 'B'
        elif percentage >= 50: grade = 'C'
        elif percentage >= 40: grade = 'D'
        else:                  grade = 'F'

        # Attendance percentage calculate karo
        total_att   = Attendance.objects.filter(student=student).count()
        present_att = Attendance.objects.filter(student=student, status='present').count()
        att_pct     = round((present_att / total_att * 100), 2) if total_att > 0 else 0

        # Report create ya update karo
        report, created = Report.objects.update_or_create(
            student=student,
            course=course,
            academic_year=academic_year,
            semester=semester,
            defaults={
                'total_marks':          total_marks,
                'obtained_marks':       obtained_marks,
                'percentage':           percentage,
                'grade':                grade,
                'attendance_percentage': att_pct,
                'remarks':              f'Auto-generated on {datetime.now().strftime("%d %b %Y")}',
            }
        )

        if created:
            generated += 1
        else:
            updated += 1

    # Summary message
    msg_parts = []
    if generated: msg_parts.append(f'{generated} new')
    if updated:   msg_parts.append(f'{updated} updated')
    if skipped:   msg_parts.append(f'{skipped} skipped (no marks/enrollment)')

    messages.success(request, f'✅ Reports generated! {" | ".join(msg_parts)}')
    return redirect('reports')


@login_required
def download_report_pdf(request):
    if not Student.objects.filter(user=request.user).exists():
        return HttpResponse("Unauthorized", status=403)

    student = Student.objects.get(user=request.user)
    marks = Mark.objects.filter(student=student).select_related('exam__subject')

    total_exams = marks.count()

    # Average %
    if total_exams > 0:
        total_pct = sum(
            (m.marks_obtained / m.exam.max_marks * 100)
            for m in marks if m.exam.max_marks > 0
        )
        avg_percentage = round(total_pct / total_exams, 1)
    else:
        avg_percentage = 0

    # Grade
    if avg_percentage >= 90: grade = 'A+'
    elif avg_percentage >= 80: grade = 'A'
    elif avg_percentage >= 70: grade = 'B+'
    elif avg_percentage >= 60: grade = 'B'
    elif avg_percentage >= 50: grade = 'C'
    elif avg_percentage >= 40: grade = 'D'
    else: grade = 'F'

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Student_Report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # HEADER
    elements.append(Paragraph("<b>Sree Narayan Guru College of Commerce</b>", styles['Title']))
    elements.append(Paragraph("Student Performance Report", styles['Heading2']))
    elements.append(Spacer(1, 15))

    # PHOTO
    photo = None
    if student.profile_image:
        img_path = os.path.join(settings.MEDIA_ROOT, str(student.profile_image))
        img_path = img_path.replace("\\", "/")

        if os.path.exists(img_path):
            photo = Image(img_path, width=80, height=100)

    # INFO
    info_data = [
        ["Name:", student.user.get_full_name()],
        ["Roll No:", student.roll_number],
        ["Department:", student.department.name],
        ["Email:", student.user.email or "-"],
        ["Phone:", student.phone or "-"],
    ]

    info_table = Table(info_data, colWidths=[100, 250])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    if photo:
        combined = Table([[photo, info_table]])
    else:
        combined = Table([["No Image", info_table]])

    elements.append(combined)
    elements.append(Spacer(1, 20))

    # MARKS TABLE
    data = [["#", "Subject", "Exam", "Max", "Marks", "%"]]

    for i, m in enumerate(marks, start=1):
        percentage = (m.marks_obtained / m.exam.max_marks * 100) if m.exam.max_marks else 0

        data.append([
            i,
            m.exam.subject.name,
            m.exam.name,
            m.exam.max_marks,
            m.marks_obtained,
            f"{round(percentage,1)}%"
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#667eea")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    elements.append(Paragraph("<b>Detailed Exam Results</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))
    elements.append(table)

    elements.append(Spacer(1, 20))

    # SUMMARY
    elements.append(Paragraph("<b>Performance Summary</b>", styles['Heading3']))
    elements.append(Paragraph(f"Total Exams: {total_exams}", styles['Normal']))
    elements.append(Paragraph(f"Average Percentage: {avg_percentage}%", styles['Normal']))
    elements.append(Paragraph(f"Overall Grade: {grade}", styles['Normal']))

    elements.append(Spacer(1, 40))

    # SIGNATURE
    sign_table = Table([
        ["Class Teacher", "HOD", "Principal"],
        ["\n\n________________", "\n\n________________", "\n\n________________"]
    ])
    sign_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))

    elements.append(sign_table)

    doc.build(elements)

    return response


# =========================
# PROFILE
# =========================
@login_required
def profile(request):
    user    = request.user
    teacher = getattr(user, 'teacher_profile', None)
    student = getattr(user, 'student_profile', None)

    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '')
        user.last_name  = request.POST.get('last_name', '')
        user.email      = request.POST.get('email', '')
        user.save()

        if teacher:
            teacher.phone = request.POST.get('phone', '')
            if 'profile_image' in request.FILES:
                teacher.profile_image = request.FILES['profile_image']
            teacher.save()

        if student:
            student.phone = request.POST.get('phone', '')
            if 'profile_image' in request.FILES:
                student.profile_image = request.FILES['profile_image']
            student.save()

        messages.success(request, '✅ Profile updated successfully!')
        return redirect('profile')

    return render(request, 'profile.html', {'teacher': teacher, 'student': student})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '✅ Password changed successfully!')
            return redirect('profile')
        else:
            messages.error(request, '❌ Please correct the errors below.')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'change_password.html', {'form': form})