"""
URL configuration for quadconnect project.

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
from allauth.account import views as account_views
from allauth.account.decorators import secure_admin_login
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path

# The admin signs in through allauth's login page, so it gets the same
# failed-login rate limit (P1-A5).
admin.site.login = secure_admin_login(admin.site.login)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Log out is public, so "Log out" in a tab whose session has expired
    # lands on the home page, not on the login form.
    path('accounts/logout/', login_not_required(account_views.logout), name='account_logout'),
    # Log in, sign up and Google sign-in (django-allauth, P1-A5).
    path('accounts/', include('allauth.urls')),
    path('', include('connect.urls')),
]
