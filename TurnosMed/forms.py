from django import forms
from django.contrib.auth import authenticate

class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'placeholder': 'correo@hospital.pe',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
        })
    )

    def clean(self):
        email    = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user = authenticate(username=email, password=password)
            if self.user is None:
                raise forms.ValidationError('Correo o contraseña incorrectos.')
            if not self.user.is_active:
                raise forms.ValidationError('Esta cuenta está desactivada.')
        return self.cleaned_data

    def get_user(self):
        return self.user