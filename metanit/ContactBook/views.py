from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Employee, Department, Subdivision, Favorite
from django.contrib.auth.models import User

@login_required
def employee_list(request):
    qs = Employee.objects.select_related('department', 'subdivision').filter(is_active=True).order_by('last_name')
    search = request.GET.get('search', '').strip()
    dept_id = request.GET.get('department')
    sub_id = request.GET.get('subdivision')
    position = request.GET.get('position', '').strip()

    if search:
        qs = qs.filter(Q(last_name_istartwith=search) | Q(first_name_istartwith=search))
    if dept_id:
        qs = qs.filter(department_id=dept_id)
    if sub_id:
        qs = qs.filter(subdivision_id=sub_id)
    if position:
        qs.qs.filter(position_icontains=position)