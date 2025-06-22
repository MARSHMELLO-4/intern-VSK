from django.urls import path
#import views 
from . import views
urlpatterns = [
    path('',views.loginSalesman,name = 'loginSalesman'),
    path('login/', views.loginSalesman, name='loginSalesman'),
    path('register/', views.registerUser, name="register"),
    path('salesmanDashboard/', views.salesmanDashboard, name='salesmanDashboard'),
    path('loginAdmin/', views.loginAdmin, name='loginAdmin'),
    path('adminDashboard/<int:category_id>', views.adminDashboard, name='adminDashboard'),
    path('uploadLeads/<int:category_id>', views.uploadLeads, name='uploadLeads'),
    # path('assignLeads/<int:lead_id>/', views.assignLead, name='assignLead'),
    path('assign-lead-ajax/', views.assign_lead_ajax, name='assign_lead_ajax'),
    path('editLead/<int:lead_id>/', views.editLead, name='editLead'),
    path('logout/',views.logoutUser, name='logoutUser'),
    path('viewLead/<int:lead_id>/', views.viewLead, name='viewLead'),
    path('deleteLead/<int:lead_id>/', views.deleteLead, name='deleteLead'),
    path('viewCategory/', views.viewCategory, name='viewCategory'),
    path('addCategory/', views.addCategory, name='addCategory'),
    path('logoutAdmin/', views.logOutAdmin, name='logoutAdmin'),
    path('viewSalesman/<str:email>/', views.viewSalesman, name='viewSalesman'),
    path('contactUs/', views.contactUs, name='term_contact'),
    path('requestPage/', views.requestPage, name='requestPage'),
    path('approve-users/', views.approve_users_view, name='approve_users'),
    path('todayLeads/', views.todayLeads, name='todayLeads'),
    path('deleteSalesman/<str:email>/', views.deleteSalesman, name='deleteSalesman'),
]
