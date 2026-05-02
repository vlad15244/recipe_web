"""
URL configuration for opc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from vars import views

urlpatterns = [
    path('', views.user_login, name='login'),    
    path('admin/', admin.site.urls),
    path('recipes/<int:pk>/edit/', views.recipe_edit, name='edit'),
    path('recipes/<int:recipe_id>/', views.one_recipe, name='recipe'), 
    path('recipes/<int:pk>/delete/', views.recipe_delete, name='delete'),       
    path('recipes/', include('vars.urls'), name='recipe_list'),
    path('realtime/', views.opcua_realtime, name='realtime'),
    path('trends/', views.trends, name='trends'),
    path('trends_month/', views.TrendsCurrentMonth.as_view(), name='trends_month'),    
    path('login/', views.user_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html', next_page = 'login'), name='logout'),    
    path('trends_pdf/', views.trends_pdf, name='trends_pdf'),
    path('trends_excel/', views.export_excel_data, name='trends_excel'),  
    path('message/', views.message, name='message'), 
    path('message_month/', views.MessageCurrentMonth.as_view(), name='message_month'), 
    path('trends_month_aggregate/', views.TrendsAggregateMonth.as_view(), name='trends_month_aggregate'), 
    path('draw/', views.draw, name='draw'),     

]
