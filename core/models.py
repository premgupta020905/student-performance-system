from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    credits = models.IntegerField(default=3)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Student(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    roll_number = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    admission_date = models.DateField()
    address = models.TextField(blank=True, null=True)
    parent_name = models.CharField(max_length=100, blank=True, null=True)
    parent_phone = models.CharField(max_length=15, blank=True, null=True)

    # 🔥 NEW (SAFE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(
        upload_to='student_profiles/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name()}"

class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    courses = models.ManyToManyField(Course)
    joining_date = models.DateField()

    # 🔥 NEW FIELDS
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(
        upload_to='teacher_profiles/',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.employee_id

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='subjects')
    max_marks = models.IntegerField(default=100)
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('student', 'course')
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.course.code}"


class Attendance(models.Model):
    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ('student', 'subject', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.subject.code} - {self.date} - {self.status}"


class Exam(models.Model):
    EXAM_TYPE_CHOICES = (
        ('midterm', 'Mid Term'),
        ('final', 'Final Exam'),
        ('quiz', 'Quiz'),
        ('assignment', 'Assignment'),
        ('practical', 'Practical'),
    )
    name = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    date = models.DateField()
    max_marks = models.IntegerField(validators=[MinValueValidator(1)])
    duration_minutes = models.IntegerField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.subject.code}"


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='marks')

    # 🔥 CI MARKS (3 Columns)
    ci_1 = models.FloatField(
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    ci_2 = models.FloatField(
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )
    ci_3 = models.FloatField(
        validators=[MinValueValidator(0)],
        null=True, blank=True
    )

    # 🔥 AUTO TOTAL
    marks_obtained = models.FloatField(default=0)

    remarks = models.TextField(blank=True, null=True)
    entered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'exam')
        ordering = ['-entered_at']

    def __str__(self):
        return f"{self.student.roll_number} - {self.exam.name} - {self.marks_obtained}"

    def calculate_total(self):
        total = 0
        for m in [self.ci_1, self.ci_2, self.ci_3]:
            if m:
                total += m
        return total

    def get_percentage(self):
        if self.exam.max_marks > 0:
            return (self.marks_obtained / self.exam.max_marks) * 100
        return 0

    def get_grade(self):
        percentage = self.get_percentage()
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B+'
        elif percentage >= 60:
            return 'B'
        elif percentage >= 50:
            return 'C'
        elif percentage >= 40:
            return 'D'
        else:
            return 'F'



class Report(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='reports')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reports')
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    total_marks = models.FloatField(default=0)
    obtained_marks = models.FloatField(default=0)
    percentage = models.FloatField(default=0)
    grade = models.CharField(max_length=5, blank=True)
    attendance_percentage = models.FloatField(default=0)
    remarks = models.TextField(blank=True, null=True)
    generated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'course', 'academic_year', 'semester')
    
    def __str__(self):
        return f"{self.student.roll_number} - {self.course.code} - {self.academic_year}"