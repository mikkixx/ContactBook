from django.contrib.auth import views as auth_views
from django.urls import path
from ContactBook import views
 
urlpatterns = [
    #аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='contactbook/login.html'), name='login'),
    path('login/', auth_views.LogoutView.as_view(next_page='contactbook:employee_list'), name='logout'),

    #сотрудники
    path('', views.employee_list, name='employee_list'),
    path('employee/<int:pk>/', views.employee_detail, name='employee_detail'),

    #избранное
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorites/<int:pk>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/<int:pk>/remove/', views.remove_from_favorite, name='remove_from_favorite'),

    #отчеты
    path('report/', views.generate_report, name='generate_report'),

    #личний каб.
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password', views.change_password, name='change_password'),
    
    #структура оргинизации
    path('structure/', views.organization_structure, name='organization_structure'),
    
    #отделы
    path('deportment/add', views.add_department, name='add_departament'),
    path('department/<int:dept_id>/edit/', views.add_department, name='edit_department'),
    path('department/<int:dept_id>/delete/', views.delete_department, name='delete_department'),
    
    #подразделения
    path('department/<int:dept_id>/subdivision/add/', views.add_subdivision, name='add_subdivision'),
    path('subdivision/<int:sub_id>/edit/', views.edit_subdivision, name='edit_subdivision'),
    path('subdivision/<int:sub_id>/delete/', views.delete_subdivision, name='delete_subdivision'),

    #изменение сотрудников
    path('employee/<int:employee_id>/edit/', views.edit_employee, name='edit_employee'),
    path('employee/<int:employee_id>/delete/', views.delete_employee, name='delete_employee'),
]