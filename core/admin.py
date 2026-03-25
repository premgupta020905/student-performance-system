from django.contrib import admin

from .models import (
    Department, Course, Student, Teacher,
    Subject, Enrollment, Attendance,
    Exam, Mark, Report
)

# ❌ User ko yahan register mat karo
# Django already default User ko register karta hai


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'credits')
    search_fields = ('name', 'code')
    list_filter = ('department',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'get_student_name', 'department', 'admission_date')
    search_fields = ('roll_number', 'user__first_name', 'user__last_name')

    def get_student_name(self, obj):
        return obj.user.get_full_name()
    get_student_name.short_description = 'Name'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_teacher_name', 'department', 'joining_date')
    search_fields = ('employee_id', 'user__first_name', 'user__last_name')
    filter_horizontal = ('courses',)

    def get_teacher_name(self, obj):
        return obj.user.get_full_name()
    get_teacher_name.short_description = 'Name'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'course', 'teacher', 'max_marks')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'enrollment_date', 'is_active')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date', 'status')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'exam_type', 'subject', 'date', 'max_marks')


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'marks_obtained', 'entered_at')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'academic_year', 'semester', 'percentage', 'grade')
