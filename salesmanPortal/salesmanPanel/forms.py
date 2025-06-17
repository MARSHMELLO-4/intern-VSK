# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'first_name', 'last_name', 'address', 'region', 'password1', 'password2']
        widgets = {
            'phone': forms.TextInput(attrs={'type': 'tel'}),
            'email': forms.EmailInput(attrs={'type': 'email'}),
        }
