from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.shortcuts import render, redirect

from users.models import User


def login_view(request):
    """
    Вход пользователя в систему.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                auth_login(request, user)
                messages.success(request, f'Добро пожаловать, {user.email}!')
                return redirect('tires:warehouse-list')
            else:
                messages.error(request, 'Неверный email или пароль')
                return redirect('users:login')
        except User.DoesNotExist:
            messages.error(request, 'Неверный email или пароль')
            return redirect('users:login')
    
    return render(request, 'users/login.html')


def logout_view(request):
    """
    Выход пользователя из системы.
    """
    auth_logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('users:login')
