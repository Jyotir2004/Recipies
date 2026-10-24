"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from vege import views

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/recipes/<int:pk>/rank/', views.admin_update_recipe, name='admin_update_recipe'),
    path('admin/recipes/<int:pk>/star/', views.admin_star_recipe, name='admin_star_recipe'),
    path('admin/recipes/<int:pk>/delete/', views.admin_delete_recipe, name='admin_delete_recipe'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('', views.recipis, name='home'),
    path('recipis/', views.recipis, name='recipis'),
    path('upload/', views.upload_recipe, name='upload_recipe'),
    path('recipes/<int:pk>/edit/', views.update_recipe, name='update_recipe'),
    path('recipes/<int:pk>/delete/', views.delete_recipe, name='delete_recipe'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
