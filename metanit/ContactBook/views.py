from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Employee, Department, Subdivision, Favorite, Contact
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
import io
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.http import JsonResponse
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.db import IntegrityError

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'employee_profile') and user.employee_profile.role == 'admin'

@login_required
def employee_list(request):
    qs = Employee.objects.select_related('department', 'subdivision').order_by('last_name')
    is_admin_user = is_admin(request.user)

    search = request.GET.get('search', '').strip()
    dept_id = request.GET.get('department')
    sub_id = request.GET.get('subdivision')
    position = request.GET.get('position', '').strip()

    # === ФИЛЬТРАЦИЯ ===
    if search:
        qs = qs.filter(Q(last_name__istartswith=search) | Q(first_name__istartswith=search))
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if sub_id:
        qs = qs.filter(subdivision_id=sub_id)
    if position:
        qs = qs.filter(position__icontains=position)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'contactbook/employee_list.html', {
        'page_obj': page_obj,
        'search': search, 'dept_id': dept_id, 'sub_id': sub_id, 'position': position,
        'departments': Department.objects.all(),
        'subdivisions': Subdivision.objects.all(),
        'is_admin': is_admin_user
    })

@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    is_fav = Favorite.objects.filter(user=request.user, employee=employee).exists()
    
    return render(request, 'contactbook/employee_detail.html', {
        'employee': employee,
        'is_favorite': is_fav,
        'is_admin': is_admin(request.user)
    })

@login_required
def toggle_favorite(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, employee=employee)

    if not created:
        fav.delete()
        messages.success(request, "Контакт удалён из избранного")
    else:
        messages.success(request, "Контакт добавлен в избранное")
        
    return redirect('contactbook:employee_detail', pk=pk)

@login_required
def favorite_list(request):
    qs = Employee.objects.filter(favorites_by__user=request.user) \
                         .select_related('department', 'subdivision') \
                         .order_by('last_name')

    search = request.GET.get('search', '').strip()
    dept_id = request.GET.get('department')
    sub_id = request.GET.get('subdivision')
    position = request.GET.get('position', '').strip()

    if search:
        qs = qs.filter(Q(last_name__istartswith=search) | Q(first_name__istartswith=search))
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if sub_id:
        qs = qs.filter(subdivision_id=sub_id)
    if position:
        qs = qs.filter(position__icontains=position)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'contactbook/favorite_list.html', {
        'page_obj': page_obj,
        'search': search, 'dept_id': dept_id, 'sub_id': sub_id, 'position': position,
        'departments': Department.objects.all(),
        'subdivisions': Subdivision.objects.all()
    })

@login_required
def remove_from_favorite(request, pk):
    if request.method == 'POST':
        fav = get_object_or_404(Favorite, user=request.user, employee_id=pk)
        fav.delete()
        messages.success(request, "Контакт удалён из избранного")
    return redirect('contactbook:favorite_list')

@login_required
def my_profile(request):
    employee = request.user.employee_profile
    return render(request, 'contactbook/my_profile.html', {
        'employee': employee,
        'user_email': request.user.email
    })

@login_required
def edit_profile(request):
    employee = request.user.employee_profile
    is_admin_user = is_admin(request.user)

    if request.method == 'POST':
        new_email = request.POST.get('email', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip() or None  
        phone = request.POST.get('phone', '').strip()
        floor = request.POST.get('floor', '').strip()
        cabinet = request.POST.get('cabinet', '').strip() or None  # 

        if is_admin_user:
            position = request.POST.get('position', '').strip()
            dept_id = request.POST.get('department')
            sub_id = request.POST.get('subdivision') or None  
        else:
            position = employee.position
            dept_id = employee.department_id
            sub_id = employee.subdivision_id

        if not last_name or not first_name or not phone or not floor or not new_email or not position or not dept_id:
            messages.error(request, "Фамилия, имя, телефон, этаж, почта, должность и отдел обязательны для заполнения")
            return redirect('contactbook:edit_profile')

        try:
            employee.last_name = last_name
            employee.first_name = first_name
            employee.middle_name = middle_name
            employee.phone = phone
            employee.floor = floor
            employee.cabinet = cabinet
            employee.position = position
            employee.department_id = dept_id
            employee.subdivision_id = sub_id
            employee.save()

            if new_email and new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                    messages.error(request, "Этот email уже зарегистрирован в системе")
                    return redirect('contactbook:edit_profile')
                User.objects.filter(id=request.user.id).update(email=new_email)

            messages.success(request, "Профиль успешно обновлён")
            return redirect('contactbook:my_profile')

        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {str(e)}")
            return redirect('contactbook:edit_profile')

    return render(request, 'contactbook/edit_profile.html', {
        'employee': employee,
        'user_email': request.user.email,
        'is_admin': is_admin_user,
        'departments': Department.objects.all() if is_admin_user else [],
        'subdivisions': Subdivision.objects.all() if is_admin_user else []
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        current_pw = request.POST.get('current_password', '').strip()
        new_pw = request.POST.get('new_password', '').strip()
        confirm_pw = request.POST.get('confirm_password', '').strip()

        if not request.user.check_password(current_pw):
            messages.error(request, "Неверный текущий пароль")
            return redirect('contactbook:change_password')

        if not (6 <= len(new_pw) <= 32):
            messages.error(request, "Новый пароль должен содержать от 6 до 32 символов")
            return redirect('contactbook:change_password')

        if new_pw != confirm_pw:
            messages.error(request, "Пароли не совпадают")
            return redirect('contactbook:change_password')

        if request.user.check_password(new_pw):
            messages.error(request, "Новый пароль не должен совпадать с предыдущим")
            return redirect('contactbook:change_password')

        request.user.set_password(new_pw)
        request.user.save()
        update_session_auth_hash(request, request.user) 
        
        messages.success(request, "Пароль успешно изменён")
        return redirect('contactbook:my_profile')

    return render(request, 'contactbook/change_password.html')

@login_required
def generate_report(request):
    """Генерация отчёта в Excel/PDF по фильтрам (только для админов)."""
    # Проверка роли администратора
    if not is_admin(request.user):
        return redirect('contactbook:employee_list')

    if request.method == 'POST':
        # Сбор параметров из формы
        report_name = request.POST.get('report_name', 'Справочник_сотрудников').strip()
        dept_id = request.POST.get('department')
        sub_id = request.POST.get('subdivision')
        position = request.POST.get('position', '').strip()
        cabinet = request.POST.get('cabinet', '').strip()
        floor = request.POST.get('floor', '').strip()
        fmt = request.POST.get('format', 'excel')

        # ✅ ИСПРАВЛЕНО: убран is_active=True (нет такого поля в модели)
        qs = Employee.objects.select_related('department', 'subdivision').all()
        
        # Применение фильтров (только если переданы)
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if sub_id:
            qs = qs.filter(subdivision_id=sub_id)
        if position:
            qs = qs.filter(position__icontains=position)
        if cabinet:
            qs = qs.filter(cabinet__icontains=cabinet)
        if floor:
            qs = qs.filter(floor__icontains=floor)

        # Получение данных для экспорта
        data = list(qs.values(
            'last_name', 'first_name', 'middle_name', 'position',
            'department__name', 'subdivision__name',
            'phone', 'floor', 'cabinet'
        ))

        if not data:
            messages.warning(request, "⚠️ Нет данных для экспорта по выбранным фильтрам")
            return redirect('contactbook:generate_report')

        # Генерация файла в выбранном формате
        if fmt == 'excel':
            return _export_excel(report_name, data)
        elif fmt == 'pdf':
            return _export_pdf(report_name, data)

    # GET: отрисовка формы с фильтрами
    return render(request, 'contactbook/generate_report.html', {
        'departments': Department.objects.all(),
        'subdivisions': Subdivision.objects.all()
    })

def _export_excel(filename, data):
    wb = Workbook()
    ws = wb.active
    ws.title = filename[:31]  
    
    headers = ['Фамилия', 'Имя', 'Отчество', 'Должность', 'Отдел', 'Подразделение', 'Телефон', 'Этаж', 'Кабинет']
    ws.append(headers)
    
    for row in data:
        ws.append([
            row.get('last_name'), row.get('first_name'), row.get('middle_name'),
            row.get('position'), row.get('department__name'), row.get('subdivision__name'),
            row.get('phone'), row.get('floor'), row.get('cabinet')
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    wb.save(response)
    return response

def _export_pdf(filename, data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    elements.append(Paragraph(f"Отчёт: {filename}", style={'fontSize': 16, 'alignment': 1}))
    elements.append(Spacer(1, 12))

    headers = ['ФИО', 'Должность', 'Отдел/Подразделение', 'Телефон', 'Место']
    table_data = [headers]
    for row in data:
        fio = f"{row['last_name']} {row['first_name']}"
        dept = f"{row['department__name']}"
        if row['subdivision__name']: dept += f" / {row['subdivision__name']}"
        place = f"{row['floor'] or ''} эт., каб. {row['cabinet'] or '—'}"
        table_data.append([fio, row['position'], dept, row['phone'], place])

    table = Table(table_data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 1*inch, 1.3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    return response

@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if not is_admin(request.user):
        if request.user.employee_profile == employee:
            return redirect('contactbook:edit_profile')
        messages.error(request, "❌ У вас нет прав для редактирования этой карточки")
        return redirect('contactbook:employee_detail', pk=employee.pk)

    if request.method == 'POST':
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip() or None
        position = request.POST.get('position', '').strip()
        dept_id = request.POST.get('department')
        sub_id = request.POST.get('subdivision') or None
        phone = request.POST.get('phone', '').strip()
        floor = request.POST.get('floor', '').strip()
        cabinet = request.POST.get('cabinet', '').strip() or None
        role = request.POST.get('role', 'user')
        new_email = request.POST.get('email', '').strip()

        if not last_name or not first_name or not phone or not floor or not new_email or not position or not dept_id:
            messages.error(request, "Фамилия, имя, телефон, этаж, почта, должность и отдел обязательны")
            return redirect('contactbook:edit_employee', pk=employee.pk)

        try:
            employee.last_name = last_name
            employee.first_name = first_name
            employee.middle_name = middle_name
            employee.position = position
            employee.department_id = dept_id
            employee.subdivision_id = sub_id
            employee.phone = phone
            employee.floor = floor
            employee.cabinet = cabinet
            employee.role = role
            employee.save()

            if new_email and employee.user_account and new_email != employee.user_account.email:
                if User.objects.filter(email=new_email).exclude(id=employee.user_account.id).exists():
                    messages.error(request, "Этот email уже используется другим аккаунтом")
                    return redirect('contactbook:edit_employee', pk=employee.pk)
                User.objects.filter(id=employee.user_account.id).update(email=new_email)

            messages.success(request, "Данные сотрудника успешно обновлены")
            return redirect('contactbook:employee_detail', pk=employee.pk)

        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {str(e)}")
            return redirect('contactbook:edit_employee', pk=employee.pk)

    return render(request, 'contactbook/edit_employee.html', {
        'employee': employee,
        'is_admin': True,
        'departments': Department.objects.all(),
        'subdivisions': Subdivision.objects.all()
    })

@login_required
def delete_employee(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Только администратор может удалять сотрудников")
        return redirect('contactbook:employee_list')

    employee = get_object_or_404(Employee, pk=pk)

    if request.method == 'POST':
        try:
            employee_name = f"{employee.last_name} {employee.first_name}"
            Favorite.objects.filter(employee=employee).delete()
            if employee.user_account:
                employee.user_account.delete()
            employee.delete()
            messages.success(request, f"Аккаунт и карточка «{employee_name}» успешно удалены")
        except Exception as e:
            messages.error(request, f"Ошибка при удалении: {str(e)}")
        return redirect('contactbook:employee_list')

    return render(request, 'contactbook/confirm_delete_employee.html', {'employee': employee})

@login_required
def organization_structure(request):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён. Только администраторы могут управлять структурой")
        return redirect('contactbook:employee_list')

    departments_qs = Department.objects.prefetch_related('subdivisions').order_by('name')
    paginator = Paginator(departments_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'contactbook/organization_structure.html', {'page_obj': page_obj})

@login_required
def edit_department(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    dept = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if not new_name:
            messages.error(request, "Название отдела не может быть пустым")
            return redirect('contactbook:edit_department', pk=dept.pk)
        if Department.objects.filter(name__iexact=new_name).exclude(pk=dept.pk).exists():
            messages.error(request, "Отдел с таким названием уже существует")
            return redirect('contactbook:edit_department', pk=dept.pk)
        try:
            dept.name = new_name
            dept.save()
            messages.success(request, f"Название отдела «{new_name}» обновлено")
        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    return render(request, 'contactbook/edit_department.html', {'department': dept})

@login_required
def add_department(request):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Название отдела не может быть пустым")
            return redirect('contactbook:add_department')
        if Department.objects.filter(name__iexact=name).exists():
            messages.error(request, "Отдел с таким названием уже существует")
            return redirect('contactbook:add_department')
        try:
            Department.objects.create(name=name)
            messages.success(request, f"Отдел «{name}» успешно добавлен")
        except Exception as e:
            messages.error(request, f"Ошибка создания: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    return render(request, 'contactbook/add_department.html')

@login_required
def delete_department(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    dept = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        if dept.employee_set.filter(is_active=True).exists():
            count = dept.employee_set.filter(is_active=True).count()
            messages.warning(request, f"Нельзя удалить отдел: в нём числится {count} сотрудник(ов). Сначала переведите их в другой отдел.")
            return redirect('contactbook:organization_structure')
        try:
            dept_name = dept.name
            dept.delete() 
            messages.success(request, f"Отдел «{dept_name}» и все его подразделения удалены")
        except Exception as e:
            messages.error(request, f"Ошибка при удалении: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    return render(request, 'contactbook/confirm_delete_department.html', {'department': dept})

@login_required
def add_subdivision(request, dept_pk):
    """Добавление подразделения в отдел (только для админов)."""
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    dept = get_object_or_404(Department, pk=dept_pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Название подразделения не может быть пустым")
            return redirect('contactbook:organization_structure')
        if Subdivision.objects.filter(name__iexact=name, department=dept).exists():
            messages.error(request, "Подразделение с таким названием уже существует в этом отделе")
            return redirect('contactbook:organization_structure')
        try:
            Subdivision.objects.create(name=name, department=dept)
            messages.success(request, f"Подразделение «{name}» добавлено в отдел «{dept.name}»")
        except Exception as e:
            messages.error(request, f"Ошибка создания: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    return render(request, 'contactbook/add_subdivision.html', {'department': dept})

@login_required
def edit_subdivision(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    sub = get_object_or_404(Subdivision, pk=pk)
    
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        if not new_name:
            messages.error(request, "Название подразделения не может быть пустым")
            return redirect('contactbook:edit_subdivision', pk=sub.pk)
        if Subdivision.objects.filter(name__iexact=new_name, department=sub.department).exclude(pk=sub.pk).exists():
            messages.error(request, "Такое подразделение уже существует в этом отделе")
            return redirect('contactbook:edit_subdivision', pk=sub.pk)
        try:
            sub.name = new_name
            sub.save()
            messages.success(request, f"Название подразделения «{new_name}» обновлено")
        except Exception as e:
            messages.error(request, f"Ошибка сохранения: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    return render(request, 'contactbook/edit_subdivision.html', {'subdivision': sub})

@login_required
def delete_subdivision(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:organization_structure')
        
    sub = get_object_or_404(Subdivision, pk=pk)
    
    if request.method == 'POST':
        employees_in_sub = Employee.objects.filter(subdivision=sub)
        emp_count = employees_in_sub.count()
        
        if emp_count > 0:
            employees_in_sub.update(subdivision=None)
            messages.info(request, f"{emp_count} сотрудник(ов) автоматически перенесён(ы) в отдел «{sub.department.name}». Подразделение удалено.")
        
        try:
            sub_name = sub.name
            sub.delete()
            messages.success(request, f"Подразделение «{sub_name}» удалено")
        except Exception as e:
            messages.error(request, f"Ошибка при удалении: {str(e)}")
        return redirect('contactbook:organization_structure')
        
    emp_count = Employee.objects.filter(subdivision=sub, is_active=True).count()
    return render(request, 'contactbook/confirm_delete_subdivision.html', {
        'subdivision': sub,
        'employee_count': emp_count
    })

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        confirm = request.POST.get('confirm_password', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip() or None
        phone = request.POST.get('phone', '').strip()
        department = request.POST.get('department', '').strip()
        subdivision = request.POST.get('subdivision', '').strip() or None
        position = request.POST.get('position', '').strip()
        floor = request.POST.get('floor', '').strip()
        cabinet = request.POST.get('cabinet', '').strip() or None

        # Валидация
        if not email or not password or not last_name or not first_name or not phone or not department or not floor:
            messages.error(request, "Все поля, отмеченные *, обязательны")
            return redirect('contactbook:register')
        
        if password != confirm:
            messages.error(request, "Пароли не совпадают")
            return redirect('contactbook:register')
        
        if len(password) < 6:
            messages.error(request, "Пароль должен содержать минимум 6 символов")
            return redirect('contactbook:register')
        
        # ✅ ПРОВЕРКА уникальности username
        if User.objects.filter(username=username).exists():
            messages.error(request, "Этот логин уже занят. Выберите другой.")
            return redirect('contactbook:register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Этот email уже зарегистрирован")
            return redirect('contactbook:register')

        try:
            # Создаём пользователя НЕактивным
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=False  # ⚡ Пользователь не может войти до подтверждения
            )
            Employee.objects.create(
                user_account=user,
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name or '',
                phone=phone,
                department_id=department,
                subdivision_id=subdivision if subdivision else None,
                position=position,
                floor=floor,
                cabinet=cabinet or ''
            )

            # 📧 Отправляем письмо с подтверждением
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Для локального тестирования используем http://127.0.0.1:8000
            activation_link = f"http://127.0.0.1:8000/activate/{uid}/{token}/"
            
            send_mail(
                subject='Подтвердите регистрацию в ContactBook',
                message=f'Привет, {username}!\n\n'
                        f'Для завершения регистрации перейдите по ссылке:\n'
                        f'{activation_link}\n\n'
                        f'Если вы не регистрировались, просто проигнорируйте это письмо.',
                from_email='your_email@gmail.com',  # Замените на вашу почту
                recipient_list=[email],
                fail_silently=False,
            )

            messages.success(request, "✅ Регистрация успешна! Проверьте почту для подтверждения email.")
            return redirect('contactbook:login')
            
        except Exception as e:
            messages.error(request, f"Ошибка регистрации: {str(e)}")
            return redirect('contactbook:register')

    return render(request, 'contactbook/register.html', {
        'departments': Department.objects.all()
    })

def activate(request, uidb64, token):
    """Подтверждение email через ссылку из письма"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        # ✅ Активируем пользователя
        user.is_active = True
        user.save()
        
        messages.success(request, "✅ Email подтверждён! Теперь вы можете войти в систему.")
        return redirect('contactbook:login')
    else:
        messages.error(request, "❌ Ссылка подтверждения недействительна или устарела.")
        return redirect('contactbook:register')

def get_subdivisions_by_dept(request):
    dept_id = request.GET.get('dept_id')
    subdivisions = []
    if dept_id and dept_id.isdigit():
        subdivisions = list(Subdivision.objects.filter(department_id=dept_id).values('id', 'name'))
    return JsonResponse({'subdivisions': subdivisions})

@login_required
def contact_list(request):
    qs = Contact.objects.all().order_by('last_name')
    
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category')
    org = request.GET.get('organization', '').strip()
    
    if search:
        qs = qs.filter(Q(last_name__istartswith=search) | 
                       Q(first_name__istartswith=search) | 
                       Q(phone__icontains=search))
    if category:
        qs = qs.filter(category=category)
    if org:
        qs = qs.filter(organization__icontains=org)
        
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'contactbook/contact_list.html', {
        'page_obj': page_obj,
        'search': search,
        'category': category,
        'organization': org,
        'categories': [('client', 'Клиент'), ('partner', 'Партнёр'), ('supplier', 'Поставщик'), ('other', 'Другое')]
    })

@login_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    
    is_owner = (contact.owner == request.user)
    is_admin_user = is_admin(request.user)
    
    return render(request, 'contactbook/contact_detail.html', {
        'contact': contact,
        'is_owner': is_owner,
        'is_admin': is_admin_user
    })

@login_required
def contact_create(request):
    if request.method == 'POST':
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip() or None
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip() or None
        organization = request.POST.get('organization', '').strip() or None
        position = request.POST.get('position', '').strip() or None
        category = request.POST.get('category', 'client')
        
        if not last_name or not first_name or not phone:
            messages.error(request, 'Фамилия, имя и телефон обязательны')
            return redirect('contactbook:contact_create')
            
        try:
            Contact.objects.create(
                last_name=last_name, first_name=first_name, middle_name=middle_name,
                phone=phone, email=email, organization=organization,
                position=position, category=category, notes=notes,
                owner=request.user 
            )
            messages.success(request, 'Контакт успешно добавлен')
            return redirect('contactbook:contact_list')
        except IntegrityError:
            messages.error(request, 'Контакт с таким телефоном или email уже существует')
            return redirect('contactbook:contact_create')
            
    return render(request, 'contactbook/contact_form.html', {'is_create': True})

@login_required
def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    
    if not is_admin(request.user) and contact.owner != request.user:
        messages.error(request, "У вас нет прав для редактирования этого контакта.")
        return redirect('contactbook:contact_detail', pk=pk)
    
    if request.method == 'POST':
        contact.last_name = request.POST.get('last_name', '').strip()
        contact.first_name = request.POST.get('first_name', '').strip()
        contact.middle_name = request.POST.get('middle_name', '').strip() or None
        contact.phone = request.POST.get('phone', '').strip()
        contact.email = request.POST.get('email', '').strip() or None
        contact.organization = request.POST.get('organization', '').strip() or None
        contact.position = request.POST.get('position', '').strip() or None
        contact.category = request.POST.get('category', 'client')
        
        if not contact.last_name or not contact.first_name or not contact.phone:
            messages.error(request, 'Фамилия, имя и телефон обязательны')
            return redirect('contactbook:contact_edit', pk=pk)
            
        try:
            contact.save()
            messages.success(request, 'Данные контакта обновлены')
            return redirect('contactbook:contact_detail', pk=pk)
        except IntegrityError:
            messages.error(request, 'Контакт с таким телефоном или email уже существует')
            return redirect('contactbook:contact_edit', pk=pk)
            
    return render(request, 'contactbook/contact_form.html', {'contact': contact, 'is_create': False})

@login_required
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    
    if not is_admin(request.user) and contact.owner != request.user:
        messages.error(request, "У вас нет прав для удаления этого контакта.")
        return redirect('contactbook:contact_detail', pk=pk)
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Контакт удалён')
        return redirect('contactbook:contact_list')
        
    return render(request, 'contactbook/contact_confirm_delete.html', {'contact': contact})