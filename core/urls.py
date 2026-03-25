from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Students ──
    path('students/', views.students_list, name='students_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),

    # ── Teachers ──
    path('teachers/add/', views.teacher_add, name='teacher_add'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),

    # ── Departments ──
    path('departments/add/', views.department_add, name='department_add'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    # ── Courses ──
    path('courses/add/', views.course_add, name='course_add'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),

    # ── Subjects ──
    path('subjects/add/', views.subject_add, name='subject_add'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    # ── Exams ──
    path('exams/add/', views.exam_add, name='exam_add'),
    path('exams/<int:pk>/delete/', views.exam_delete, name='exam_delete'),

    # ── Attendance ──
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/mark/<int:subject_id>/', views.mark_attendance, name='mark_attendance'),

    # ── Marks ──
    path('marks/', views.marks_list, name='marks_list'),
    path('marks/enter/<int:exam_id>/', views.enter_marks, name='enter_marks'),

    # ── Reports ──
    path('reports/', views.reports, name='reports'),
    path('reports/pdf/', views.download_report_pdf, name='download_report_pdf'),
    # ✅ NEW: Ek click mein sab students ke reports generate karo
    path('reports/generate-all/', views.generate_all_reports, name='generate_all_reports'),

    # ── Profile ──
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]