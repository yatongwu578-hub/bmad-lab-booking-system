from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField

from .models import User


MAX_ACCOUNT_PASSWORD_LENGTH = 4096
MAX_USERNAME_CODE_POINTS = User._meta.get_field(User.USERNAME_FIELD).max_length


class AccountAuthenticationForm(AuthenticationForm):
    username = UsernameField(
        max_length=MAX_USERNAME_CODE_POINTS,
        validators=[User.username_validator],
    )
    password = forms.CharField(
        strip=False,
        max_length=MAX_ACCOUNT_PASSWORD_LENGTH,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A browser can silently truncate at maxlength before Django validates the value.
        self.fields["username"].widget.attrs.pop("maxlength", None)
        self.fields["password"].widget.attrs.pop("maxlength", None)
