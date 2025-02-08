from django import forms
from django.contrib.auth.forms import UserCreationForm
from farminsight_dashboard_backend.models import Userprofile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text='Required')
    name = forms.CharField(max_length=200)

    class Meta:
        model = Userprofile
        fields = ('name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save()
        user.username = user.email
        user.save()
        return user


class LoginForm(forms.Form):
    email = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)