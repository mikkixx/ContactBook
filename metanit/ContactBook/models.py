from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название отдела')

    class Meta:
        verbose_name_plural = 'Отделы'
    def __str__(self):
        return self.name
    
class Subdivision(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название подразделения')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subdivisions', verbose_name='Родительский отдел')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'department'], name='unique_subdivision_name_per_dept')
        ]
        verbose_name_plural = 'Подразделения'
    def __str__(self):
        return self.name

class Employee(models.Model):
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')  
    first_name = models.CharField(max_length=50, verbose_name='Имя')  
    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Отчество') 

    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name='Отдел') 
    subdivision = models.ForeignKey(Subdivision, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Подразделение')
    position = models.CharField(max_length=100, verbose_name='Должность')

    phone = models.CharField(max_length=20, unique=True, verbose_name='Телефон')
    floor = models.CharField(max_length=50, verbose_name='Этаж')
    cabinet = models.CharField(max_length=50, blank=True, null=True, verbose_name='Кабинет')

    role = models.CharField(
        max_length=20,
        choices=[('user', 'Пользователь'), ('admin', 'Администратор')],
        default='user',
        verbose_name='Роль'
    )
    user_account = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_profile', verbose_name='Аккаунт входа')
    
    class Meta:
        verbose_name_plural = 'Сотрудники'
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
    
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', verbose_name='Пользователь')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='favorites_by', verbose_name='Сотрудник')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'employee'], name='unique_favorites_entry')
        ]
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f"{self.user.email} -> {self.employee}"
    
class Contact(models.Model):
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')  
    first_name = models.CharField(max_length=50, verbose_name='Имя')  
    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Отчество') 
    phone = models.CharField(max_length=20, unique=True, verbose_name='Телефон')
    email = models.CharField(max_length=150, unique=True, blank=True, null=True, verbose_name='Почта')
    organization = models.CharField(max_length=100, blank=True, null=True, verbose_name='Организация')
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name='Должность')
    category = models.CharField(max_length=20, choices=[('client', 'Клиент'), ('partner', 'Партнёр'), ('supplier', 'Поставщик'), ('other', 'Другое')], default='client', verbose_name='Категория')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Ответственный')

    class Meta:
        verbose_name = 'Внешний контакт'
        verbose_name_plural = 'Внешние контакты'
        ordering = ['last_name', 'first_name'] 

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.organization or 'Без организации'})"