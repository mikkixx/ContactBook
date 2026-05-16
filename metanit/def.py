from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from ContactBook.models import Department, Subdivision, Employee, Favorite

# Вспомогательная функция для проверки роли
def is_admin(user):
    """Возвращает True, если пользователь имеет роль администратора."""
    employee = getattr(user, 'employee_profile', None)
    return employee is not None and employee.role == 'admin'

# =============================================================================
# 4) Редактирование информации сотрудника
# =============================================================================
@login_required
def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    current_is_admin = is_admin(request.user)

    # Проверка прав: админ или редактирование собственной карточки
    if not current_is_admin and request.user.employee_profile != employee:
        messages.error(request, "У вас нет прав для редактирования этой карточки.")
        return redirect('employee_detail', employee_id=employee.id)

    if request.method == 'POST':
        if current_is_admin:
            # Администратор меняет все поля
            employee.last_name = request.POST.get('last_name')
            employee.first_name = request.POST.get('first_name')
            employee.middle_name = request.POST.get('middle_name')
            employee.department_id = request.POST.get('department')
            sub_id = request.POST.get('subdivision')
            employee.subdivision_id = sub_id if sub_id else None
            employee.phone = request.POST.get('phone')
            employee.floor = request.POST.get('floor')
            employee.cabinet = request.POST.get('cabinet')
            employee.role = request.POST.get('role', 'user')
            employee.position = request.POST.get('position')
        else:
            # Обычный пользователь меняет только разрешенные поля
            # Email хранится в модели User
            if request.POST.get('email') and request.user.email != request.POST.get('email'):
                request.user.email = request.POST.get('email')
                request.user.save()

        try:
            employee.full_clean()  # Проверка unique и форматов
            employee.save()
            messages.success(request, "Данные успешно обновлены.")
        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {e}")

        return redirect('employee_detail', employee_id=employee.id)

    return render(request, 'employees/edit_employee.html', {
        'employee': employee,
        'is_admin': current_is_admin
    })

# =============================================================================
# 5) Удаление аккаунта сотрудника
# =============================================================================
@login_required
def delete_employee (request, employee_id):
    if not is_admin(request.user):
        messages.error(request, "Только администратор может удалять аккаунты.")
        return redirect('employee_list')
    
    employee = get_object_or_404(Employee, id = employee_id)
    
    if request.method == 'POST':
        user_account = employee.user_account
        Favorite.objects.filter(employee=employee).delete()

        if user_account:
            user_account.delete()
        else:
            employee.delete()
        messages.success(request, "Аккаунт и карточка сотрудника удалены.")
        return redirect('employee_list')
    return render(request, 'employees/confirm_delete_employee.html', {'employee': employee})

# =============================================================================
# 6) Просмотр страницы «Структура организации»
# =============================================================================
@login_required
def organization_structure(request):
    # prefetch_related оптимизирует запросы при раскрытии подразделений
    departments_qs = Department.objects.prefetch_related('subdivisions').order_by('name')
    
    paginator = Paginator(departments_qs, 5)  # По 5 отделов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'structure/structure.html', {'page_obj': page_obj})

# Примечание: Пункт 10 (Просмотр списка подразделений) реализуется на фронтенде.
# Данные уже переданы через prefetch_related. JS/HTMX просто показывает/скрывает блок <ul> с подразделениями.

# =============================================================================
# 7) Смена названия отдела
# =============================================================================
@login_required
def edit_department(request, dept_id):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        new_name = request.POST.get('name')
        dept.name = new_name
        try:
            dept.full_clean()
            dept.save()
            messages.success(request, "Название отдела обновлено.")
        except IntegrityError:
            messages.error(request, "Отдел с таким названием уже существует.")
        return redirect('organization_structure')
        
    return render(request, 'structure/edit_department.html', {'department': dept})

# =============================================================================
# 8) Добавление отдела
# =============================================================================
@login_required
def add_department(request):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    if request.method == 'POST':
        name = request.POST.get('name')
        try:
            Department.objects.create(name=name)
            messages.success(request, "Отдел успешно добавлен.")
        except IntegrityError:
            messages.error(request, "Отдел с таким названием уже существует.")
        return redirect('organization_structure')
        
    return render(request, 'structure/add_department.html')

# =============================================================================
# 9) Удаление отдела
# =============================================================================
@login_required
def delete_department(request, dept_id):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        if dept.employee_set.exists():
            messages.warning(request, "Удалить отдел нельзя: в нем закреплены сотрудники. Переместите их в другой отдел.")
            return redirect('organization_structure')
            
        # on_delete=CASCADE в Subdivision автоматически удалит вложенные подразделения
        dept.delete()
        messages.success(request, "Отдел и все его подразделения удалены.")
        return redirect('organization_structure')
        
    return render(request, 'structure/confirm_delete_dept.html', {'department': dept})

# =============================================================================
# 11) Добавление подразделения
# =============================================================================
@login_required
def add_subdivision(request, dept_id):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    dept = get_object_or_404(Department, id=dept_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        try:
            Subdivision.objects.create(name=name, department=dept)
            messages.success(request, "Подразделение добавлено.")
        except IntegrityError:
            messages.error(request, "Подразделение с таким названием уже существует в этом отделе.")
        return redirect('organization_structure')
        
    return render(request, 'structure/add_subdivision.html', {'department': dept})

# =============================================================================
# 12) Смена названия подразделения
# =============================================================================
@login_required
def edit_subdivision(request, sub_id):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    sub = get_object_or_404(Subdivision, id=sub_id)
    if request.method == 'POST':
        new_name = request.POST.get('name')
        sub.name = new_name
        try:
            sub.full_clean()
            sub.save()
            messages.success(request, "Название подразделения обновлено.")
        except IntegrityError:
            messages.error(request, "Такое подразделение уже существует в этом отделе.")
        return redirect('organization_structure')
        
    return render(request, 'structure/edit_subdivision.html', {'subdivision': sub})

# =============================================================================
# 13) Удаление подразделения
# =============================================================================
@login_required
def delete_subdivision(request, sub_id):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещен.")
        return redirect('organization_structure')
        
    sub = get_object_or_404(Subdivision, id=sub_id)
    if request.method == 'POST':
        employees_in_sub = Employee.objects.filter(subdivision=sub)
        if employees_in_sub.exists():
            # Автоматический перенос сотрудников в родительский отдел (согласно ТЗ)
            parent_dept = sub.department
            employees_in_sub.update(subdivision=None, department=parent_dept)
            messages.info(request, f"Сотрудники автоматически перемещены в отдел «{parent_dept.name}».")
            
        sub.delete()
        messages.success(request, "Подразделение удалено.")
        return redirect('organization_structure')
        
    return render(request, 'structure/confirm_delete_sub.html', {'subdivision': sub})