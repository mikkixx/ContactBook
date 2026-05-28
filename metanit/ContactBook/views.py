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
from django.http import JsonResponse
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.db import IntegrityError
from .utils import normalize_phone
import re
import logging
from django.utils import timezone 

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'employee_profile') and user.employee_profile.role == 'admin'

@login_required
def employee_list(request):
    qs = Employee.objects.select_related('department', 'subdivision', 'user_account').order_by('last_name')
    is_admin_user = is_admin(request.user)

    search = request.GET.get('search', '').strip()
    dept_id = request.GET.get('department')
    sub_id = request.GET.get('subdivision')
    position = request.GET.get('position', '').strip()

    # === ФИЛЬТРАЦИЯ ===
    if search:
        search_escaped = re.escape(search)
        pattern = f'^{search_escaped}'
        qs = qs.filter(
            Q(last_name__iregex=pattern) | 
            Q(first_name__iregex=pattern)
        )
    if dept_id and dept_id != 'None':
        qs = qs.filter(department_id=dept_id)
    if sub_id and sub_id != 'None':
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
        'is_admin': is_admin(request.user),
        'departments': Department.objects.all(),
        'subdivisions': Subdivision.objects.all()
    })

@login_required
def toggle_favorite(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, employee=employee)

    if not created:
        fav.delete()
        
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
        search_escaped = re.escape(search)
        pattern = f'^{search_escaped}'
        qs = qs.filter(
            Q(last_name__iregex=pattern) | 
            Q(first_name__iregex=pattern)
        )
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
    context = {
        'employee': employee,
        'user_email': request.user.email
    }
    if employee.role == 'admin':
        context['departments'] = Department.objects.all()
        context['subdivisions'] = Subdivision.objects.all()
        
    return render(request, 'contactbook/my_profile.html', context)

@login_required
def edit_profile(request):
    employee = request.user.employee_profile
    
    if request.method == 'POST':
        try:
            new_email = request.POST.get('email', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            middle_name = request.POST.get('middle_name', '').strip() or None
            phone = request.POST.get('phone', '').strip()
            floor = request.POST.get('floor', '').strip()
            cabinet = request.POST.get('cabinet', '').strip() or None

            is_admin_user = request.user.is_staff or getattr(employee, 'role', None) == 'admin'
            position = employee.position
            dept_id = employee.department_id
            sub_id = employee.subdivision_id

            if is_admin_user:
                position = request.POST.get('position', '').strip()
                dept_id = request.POST.get('department')
                sub_id = request.POST.get('subdivision') or None

            if not all([last_name, first_name, phone, floor, new_email, dept_id]):
                return JsonResponse({'success': False, 'message': 'Заполните все обязательные поля'}, status=400)

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
                    return JsonResponse({'success': False, 'message': 'Этот email уже зарегистрирован'}, status=400)
                User.objects.filter(id=request.user.id).update(email=new_email)

            return JsonResponse({'success': True, 'message': 'Профиль успешно обновлён'})

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления профиля: {e}", exc_info=True)
            return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'}, status=500)

    departments = employee.department.__class__.objects.all() if hasattr(employee, 'department') else []
    subdivisions = employee.subdivision.__class__.objects.all() if hasattr(employee, 'subdivision') else []
    
    return render(request, 'contactbook/my_profile.html', {
        'employee': employee,
        'user_email': request.user.email,
        'departments': departments,
        'subdivisions': subdivisions
    })

@login_required
def change_password(request):
    if request.method != 'POST':
        return redirect('contactbook:my_profile')

    try:
        current_pw = request.POST.get('current_password', '').strip()
        new_pw = request.POST.get('new_password', '').strip()
        confirm_pw = request.POST.get('confirm_password', '').strip()

        if not request.user.check_password(current_pw):
            return JsonResponse({'success': False, 'message': 'Неверный текущий пароль'}, status=400)
        if not (6 <= len(new_pw) <= 32):
            return JsonResponse({'success': False, 'message': 'Пароль должен быть от 6 до 32 символов'}, status=400)
        if new_pw != confirm_pw:
            return JsonResponse({'success': False, 'message': 'Пароли не совпадают'}, status=400)
        if request.user.check_password(new_pw):
            return JsonResponse({'success': False, 'message': 'Новый пароль не должен совпадать с предыдущим'}, status=400)

        request.user.set_password(new_pw)
        request.user.save()
        update_session_auth_hash(request, request.user) 
        return JsonResponse({'success': True, 'message': 'Пароль успешно изменён'})

    except Exception as e:
        logging.error(f"Ошибка смены пароля: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': 'Ошибка сервера. Попробуйте позже.'}, status=500)

@login_required
def edit_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method != 'POST':
        return render(request, 'contactbook/edit_employee.html', {
            'employee': employee,
            'departments': Department.objects.all(),
            'subdivisions': Subdivision.objects.all()
        })

    if not is_admin(request.user):
        if request.user.employee_profile == employee:
            return redirect('contactbook:edit_profile')
        return JsonResponse({'success': False, 'message': 'У вас нет прав для редактирования этой карточки'}, status=403)

    try:
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

        if not all([last_name, first_name, phone, floor, new_email, position, dept_id]):
            return JsonResponse({'success': False, 'message': 'Заполните все обязательные поля'}, status=400)

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
                return JsonResponse({'success': False, 'message': 'Этот email уже используется другим аккаунтом'}, status=400)
            User.objects.filter(id=employee.user_account.id).update(email=new_email)

        return JsonResponse({'success': True, 'message': 'Данные сотрудника успешно обновлены'})

    except Exception as e:
        logging.error(f"Ошибка обновления сотрудника #{pk}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'}, status=500)

@login_required
def delete_employee(request, pk):
    if request.method != 'POST':
        manager = getattr(Employee, 'all_objects', Employee.objects)
        employee = get_object_or_404(manager, pk=pk)
        return render(request, 'contactbook/confirm_delete_employee.html', {'employee': employee})

    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Только администратор может удалять сотрудников'}, status=403)

    try:
        manager = getattr(Employee, 'all_objects', Employee.objects)
        employee = get_object_or_404(manager, pk=pk)

        if getattr(employee, 'is_deleted', False):
            return JsonResponse({'success': False, 'message': 'Этот сотрудник уже удалён'}, status=400)

        employee.is_deleted = True
        employee.deleted_at = timezone.now()
        employee.save()

        if employee.user_account:
            employee.user_account.is_active = False
            employee.user_account.save()

        return JsonResponse({
            'success': True, 
            'message': f'Карточка «{employee.last_name} {employee.first_name}» перемещена в корзину'
        })

    except Exception as e:
        logging.error(f"Ошибка удаления сотрудника #{pk}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': f'Ошибка сервера: {str(e)}'}, status=500)

@login_required
def restore_employee(request, pk):
    """Восстановление удалённого сотрудника (только для админов)"""
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:employee_list')
    
    # ✅ Ищем среди удалённых
    employee = get_object_or_404(Employee.all_objects, pk=pk, is_deleted=True)
    
    if request.method == 'POST':
        try:
            employee.restore()
            
            # Активируем учётную запись
            if employee.user_account:
                employee.user_account.is_active = True
                employee.user_account.save()
            
            messages.success(request, f"Сотрудник {employee} восстановлен")
        except Exception as e:
            messages.error(request, f"Ошибка при восстановлении: {str(e)}")
    
    return redirect('contactbook:deleted_employees')  # Или куда хочешь

@login_required
def deleted_employees(request):
    """Список удалённых сотрудников (только для админов)"""
    if not is_admin(request.user):
        messages.error(request, "Доступ запрещён")
        return redirect('contactbook:employee_list')
    
    search = request.GET.get('search', '').strip()
    position = request.GET.get('position', '').strip()
    sort_order = request.GET.get('sort', 'desc')


    qs = Employee.all_objects.filter(is_deleted=True).select_related('department')
    
    if search:
        search_escaped = re.escape(search)
        pattern = f'^{search_escaped}'
        
        qs = qs.filter(
            Q(last_name__iregex=pattern) |
            Q(first_name__iregex=pattern) |
            Q(middle_name__iregex=pattern)
        )

    if position:
        qs = qs.filter(position__icontains=position)
    
    if sort_order == 'asc':
        qs = qs.order_by('deleted_at')
    else:
        qs = qs.order_by('-deleted_at')

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'contactbook/deleted_employees.html', {
        'page_obj': page_obj,
        'is_admin': True,
        'search': search,
        'position': position,
        'sort_order': sort_order
    })

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
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)

    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)

    dept = get_object_or_404(Department, pk=pk)
    new_name = request.POST.get('name', '').strip()

    if not new_name:
        return JsonResponse({'success': False, 'message': 'Название не может быть пустым'}, status=400)

    if new_name.lower() == dept.name.lower():
        return JsonResponse({'success': False, 'message': f'Отдел уже называется «{dept.name}»'}, status=400)

    if Department.objects.filter(name__iexact=new_name).exists():
        return JsonResponse({'success': False, 'message': 'Отдел с таким названием уже существует'}, status=400)

    try:
        old_name = dept.name
        dept.name = new_name
        dept.save()
        return JsonResponse({'success': True, 'message': f'Название обновлено: «{old_name}» → «{new_name}»'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сохранения: {str(e)}'}, status=500)

@login_required
def add_department(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)

    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'message': 'Название не может быть пустым'}, status=400)

    if Department.objects.filter(name__iexact=name).exists():
        return JsonResponse({'success': False, 'message': 'Отдел уже существует'}, status=400)

    try:
        dept = Department.objects.create(name=name)
        return JsonResponse({
            'success': True,
            'message': f'Отдел «{name}» успешно добавлен',
            'dept_id': dept.id,
            'dept_name': dept.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'}, status=500)

@login_required
def delete_department(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)

    dept = get_object_or_404(Department, pk=pk)

    if dept.employee_set.exists():
        count = dept.employee_set.count()
        return JsonResponse({
            'success': False, 
            'message': f'Нельзя удалить: в отделе числится {count} сотрудник(ов). Переведите их в другой отдел.'
        }, status=400)

    try:
        dept_name = dept.name
        dept.delete()
        return JsonResponse({'success': True, 'message': f'Отдел «{dept_name}» и все подразделения удалены'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка при удалении: {str(e)}'}, status=500)

@login_required
def add_subdivision(request, dept_pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)

    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)

    dept = get_object_or_404(Department, pk=dept_pk)
    name = request.POST.get('name', '').strip()

    if not name:
        return JsonResponse({'success': False, 'message': 'Название не может быть пустым'}, status=400)

    if Subdivision.objects.filter(name__iexact=name, department=dept).exists():
        return JsonResponse({'success': False, 'message': 'Такое подразделение уже есть в этом отделе'}, status=400)

    try:
        Subdivision.objects.create(name=name, department=dept)
        return JsonResponse({
            'success': True,
            'message': f'Подразделение «{name}» добавлено в отдел «{dept.name}»'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'}, status=500)

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Subdivision

@login_required
def edit_subdivision(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)

    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)

    sub = get_object_or_404(Subdivision, pk=pk)
    new_name = request.POST.get('name', '').strip()

    if not new_name:
        return JsonResponse({'success': False, 'message': 'Название не может быть пустым'}, status=400)

    if new_name.lower() == sub.name.lower():
        return JsonResponse({'success': False, 'message': f'Подразделение уже называется «{sub.name}»'}, status=400)

    if Subdivision.objects.filter(name__iexact=new_name, department=sub.department).exists():
        return JsonResponse({'success': False, 'message': 'Такое подразделение уже существует в этом отделе'}, status=400)

    try:
        old_name = sub.name
        sub.name = new_name
        sub.save()
        return JsonResponse({'success': True, 'message': f'Название обновлено: «{old_name}» → «{new_name}»'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка сохранения: {str(e)}'}, status=500)

@login_required
def delete_subdivision(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Метод не поддерживается'}, status=405)
    
    if not is_admin(request.user):
        return JsonResponse({'success': False, 'message': 'Доступ запрещён'}, status=403)
    
    sub = get_object_or_404(Subdivision, pk=pk)
    target_dept = sub.department
    
    if request.method == 'POST':
        employees_in_sub = Employee.objects.filter(subdivision=sub)
        emp_count = employees_in_sub.count()
        
        if emp_count > 0:
            employees_in_sub.update(subdivision=None)
        
        try:
            sub_name = sub.name
            sub.delete()
            msg = f"Подразделение «{sub_name}» удалено"
            if emp_count > 0:
                msg += f". {emp_count} сотрудник(ов) перенесён(ы) в отдел «{target_dept.name}»"
            return JsonResponse({'success': True, 'message': msg})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Ошибка при удалении: {str(e)}'}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Некорректный запрос'}, status=400)

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
    is_admin_user = is_admin(request.user)  
    qs = Contact.objects.all()
    
    mine_only = request.GET.get('mine_only') == 'on'
    if mine_only:
        qs = qs.filter(owner=request.user)
        
    search = request.GET.get('search', '').strip()
    position = request.GET.get('position', '').strip()
    org = request.GET.get('organization', '').strip()
    category = request.GET.get('category', '').strip()
    
    if search:
        search_escaped = re.escape(search)
        pattern = f'^{search_escaped}'
        qs = qs.filter(
            Q(last_name__iregex=pattern) | 
            Q(first_name__iregex=pattern)
        )
    if position:
        qs = qs.filter(position__icontains=position)
    if org:
        qs = qs.filter(organization__icontains=org)
    if category:
        qs = qs.filter(category=category)
        
    qs = qs.order_by('last_name')
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'contactbook/contact_list.html', {
        'page_obj': page_obj,
        'search': search,
        'position': position,
        'organization': org,
        'category': category,
        'mine_only': mine_only, 
        'categories': [('client', 'Клиент'), ('partner', 'Партнёр'), ('supplier', 'Поставщик'), ('other', 'Другое')],
        'is_admin': is_admin_user
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
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Фамилия, имя и телефон обязательны'}, status=400)
            messages.error(request, 'Фамилия, имя и телефон обязательны')
            return redirect('contactbook:contact_create')
            
        try:
            Contact.objects.create(
                last_name=last_name,
                first_name=first_name,
                middle_name=middle_name,
                phone=phone,
                email=email,
                organization=organization,
                position=position,
                category=category,
                owner=request.user
            )
            msg = 'Контакт успешно добавлен'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
            return redirect('contactbook:contact_list')
            
        except IntegrityError:
            msg = 'Контакт с таким телефоном или email уже существует'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
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
            return redirect('contactbook:contact_detail', pk=pk)
            
        try:
            contact.save()
            messages.success(request, 'Данные контакта обновлены')
            return redirect('contactbook:contact_detail', pk=pk)
        except IntegrityError:
            messages.error(request, 'Контакт с таким телефоном или email уже существует')
            return redirect('contactbook:contact_detail', pk=pk)

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