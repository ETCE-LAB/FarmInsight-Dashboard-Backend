from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import loader
from django.urls import reverse
from farminsight_dashboard_backend.forms import SignUpForm, LoginForm, ForgotPasswordForm
from farminsight_dashboard_backend.models import Userprofile
from farminsight_dashboard_backend.services import create_single_use_token, send_html_email
from farminsight_dashboard_backend.services.auth_services import get_user_from_single_use_token


en_texts = {
    'invalid_username': 'Invalid username or password.',
    'logout_success': 'Successfully logged out!',
    'pw_update_success': 'Your password was successfully updated!',
    'error_below': 'Please correct the error below.',
    'pw_reset': 'FarmInsight Password Reset',
    'request_received': 'Your request has been received. Check your email account for further instructions.',
    'invalid_token': 'Invalid token. Please try to reset your password again.',
}

de_texts = {
    'invalid_username': 'Nutzername oder Passwort ist fehlerhaft.',
    'logout_success': 'Erfolgreich abgemeldet!',
    'pw_update_success': 'Ihr Passwort wurde erfolgreich geändert!',
    'error_below': 'Bitte korrigieren Sie den Fehler unten.',
    'pw_reset': 'FarmInsight Passwort zurück setzen',
    'request_received': 'Ihre Anfrage wurde entgegengenommen. Prüfen Sie ihr Email Postfach für weitere Anweisungen.',
    'invalid_token': 'Invalide Anfrage. Bitte versuchen Sie erneut ihr Passwort zurück zu setzen.',
}

def get_text(key: str, code: str) -> str:
    if code == 'de':
        return de_texts.get(key, 'unbekannter text')
    return en_texts.get(key, 'unknown text')


def get_language_code_from_request(request):
    """
    Having the query parameter next=<url> breaks django's internal representation because all subsequent parameters are
    treated as part of the next url instead of as parameters of the base request, this means to get the language_code
    parameter send in from the frontend it is necessary to manually split the existing parameters up and look for the
    language_code parameter in there
    """
    if 'lc' in request.GET:
        return request.GET['lc']

    for key, value in request.GET.items():
        if 'lc=de' in value:
            return 'de'

    return 'en'


def signup_view(request):
    lc = get_language_code_from_request(request)
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
    return render(request, 'signup.html', {'form': form, 'lc': lc})


def login_view(request):
    lc = get_language_code_from_request(request)
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
                messages.error(request, get_text('invalid_username', lc))
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form, 'lc': lc})


@login_required
def logout_view(request):
    lc = get_language_code_from_request(request)
    logout(request)
    messages.success(request, get_text('logout_success', lc))
    return render(request, 'return.html', {'landing': settings.FRONTEND_URL, 'lc': lc})


@login_required
def change_password_view(request):
    lc = get_language_code_from_request(request)
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, get_text('pw_update_success', lc))
            logout(request)
            return render(request, 'return.html', {'landing': settings.FRONTEND_URL, 'lc': lc})
        else:
            messages.error(request, get_text('error_below', lc))
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form, 'lc': lc})


def forgot_password_view(request):
    lc = get_language_code_from_request(request)
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user : Userprofile = Userprofile.objects.filter(email=form.cleaned_data.get('email')).first()
            if user:
                DURATION = 30
                token = create_single_use_token(user, DURATION)
                url = f'{settings.SITE_URL}{reverse('reset_password_view')}?token={token}&lc={lc}'
                body = loader.render_to_string('email\\password_reset_link.html', {'reset_link': url, 'duration': DURATION, 'lc': lc})
                send_html_email(user.email, get_text('pw_reset', lc), body)
            messages.success(request, get_text('request_received', lc))
        else:
            messages.error(request, get_text('error_below', lc))
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form, 'lc': lc})


def reset_password_view(request):
    lc = get_language_code_from_request(request)
    if request.method == 'POST':
        user = get_user_from_single_use_token(request.GET.get('token'))
        if user:
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, get_text('pw_update_success', lc))
                return render(request, 'return.html', {'landing': settings.FRONTEND_URL, 'lc': lc})
        else:
            messages.error(request, get_text('invalid_token', lc))
            return render(request, 'return.html', {'landing': settings.FRONTEND_URL, 'lc': lc})
    else:
        user = get_user_from_single_use_token(request.GET.get('token'), False)
        if user:
            form = SetPasswordForm(user)
        else:
            messages.error(request, get_text('invalid_token', lc))
            return render(request, 'return.html', {'landing': settings.FRONTEND_URL, 'lc': lc})

    return render(request, 'reset_password.html', {'form': form, 'lc': lc})