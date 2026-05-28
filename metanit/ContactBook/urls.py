from django.contrib.auth import views as auth_views
from django.urls import path
from ContactBook import views

app_name = 'contactbook'  

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='contactbook/login.html'), name='login'),
    path('register/', views.register, name='register'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('logout/', auth_views.LogoutView.as_view(next_page='contactbook:employee_list'), name='logout'),
    
    path('', views.employee_list, name='employee_list'),
    path('employee/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('contact/<int:pk>/toggle-favorite/', views.toggle_contact_favorite, name='toggle_contact_favorite'),
path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorites/<int:pk>/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/<int:pk>/remove/', views.remove_from_favorite, name='remove_from_favorite'),
    path('report/', views.generate_report, name='generate_report'),
    path('profile/', views.my_profile, name='my_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('structure/', views.organization_structure, name='organization_structure'),
    path('department/add/', views.add_department, name='add_department'),
    path('department/<int:pk>/edit/', views.edit_department, name='edit_department'),
    path('department/<int:pk>/delete/', views.delete_department, name='delete_department'),
    path('department/<int:dept_pk>/subdivision/add/', views.add_subdivision, name='add_subdivision'),
    path('subdivision/<int:pk>/edit/', views.edit_subdivision, name='edit_subdivision'),
    path('subdivision/<int:pk>/delete/', views.delete_subdivision, name='delete_subdivision'),
    path('employee/<int:pk>/edit/', views.edit_employee, name='edit_employee'),
    path('employee/<int:pk>/delete/', views.delete_employee, name='delete_employee'),
    path('employees/deleted/', views.deleted_employees, name='deleted_employees'),
    path('employee/<int:pk>/restore/', views.restore_employee, name='restore_employee'),
    path('api/subdivisions/', views.get_subdivisions_by_dept, name='get_subdivisions'),
    path('contacts/', views.contact_list, name='contact_list'),
    path('contacts/add/', views.contact_create, name='contact_create'),
    path('contacts/<int:pk>/', views.contact_detail, name='contact_detail'),
    path('contacts/<int:pk>/edit/', views.contact_edit, name='contact_edit'),
    path('contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
]