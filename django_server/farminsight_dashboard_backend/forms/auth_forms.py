from django import forms
from django.forms import ValidationError
from django.contrib.auth.forms import UserCreationForm
from farminsight_dashboard_backend.models import Userprofile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text='Required')
    name = forms.CharField(max_length=200)

    class Meta:
        model = Userprofile
        fields = ('name', 'email', 'password1', 'password2')

    def clean_email(self):
        data = self.cleaned_data['email']
        if len(Userprofile.objects.filter(email=data).all()) > 0:
            raise ValidationError("User with this email already exists.")

        return data

    def save(self, commit=True):
        user = super().save()
        user.username = user.email
        user.save()
        return user


class LoginForm(forms.Form):
    email = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()
