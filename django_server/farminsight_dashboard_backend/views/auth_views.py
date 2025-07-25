from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import loader
from django.urls import reverse
from farminsight_dashboard_backend.forms import SignUpForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
from farminsight_dashboard_backend.models import Userprofile
from farminsight_dashboard_backend.services import create_single_use_token, send_html_email
from farminsight_dashboard_backend.services.auth_services import get_user_from_single_use_token


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect(request.GET.get('next'))
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(request.GET.get('next'))
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return render(request, 'success.html', {'landing': settings.FRONTEND_URL})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            logout(request)
            return render(request, 'success.html', {'landing': settings.FRONTEND_URL})
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user : Userprofile = Userprofile.objects.filter(email=form.cleaned_data.get('email')).first()
            if user:
                DURATION = 30
                token = create_single_use_token(user, DURATION)
                url = f'{settings.SITE_URL}{reverse('reset_password_view')}?token={token}'
                body = loader.render_to_string('email\\password_reset_link.html', { 'reset_link': url, 'duration': DURATION })
                send_html_email(user.email, 'Farminsight Password Reset', body)
            messages.success(request, 'Your request has been received. Check your email account for further instructions.')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form})


def reset_password_view(request):
    if request.method == 'POST':
        user = get_user_from_single_use_token(request.GET.get('token'))
        if user:
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, 'Your password was successfully updated!')
                return render(request, 'success.html', {'landing': settings.FRONTEND_URL})
        else:
            messages.error(request, 'Invalid token. Please try to reset your password again')
            return render(request, 'error.html', {'landing': settings.FRONTEND_URL})
    else:
        user = get_user_from_single_use_token(request.GET.get('token'), False)
        if user:
            form = SetPasswordForm(user)
        else:
            messages.error(request, 'Invalid token. Please try to reset your password again')
            return render(request, 'error.html', {'landing': settings.FRONTEND_URL})

    return render(request, 'reset_password.html', {'form': form})