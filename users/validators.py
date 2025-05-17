# File: users/validatos.py
# Author: Oluwatobiloba Light
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class PasswordComplexityValidator:
    def validate(self, password, user=None):
        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )

        # Check for at least one number
        if not re.search(r"[0-9]", password):
            raise ValidationError(
                _("Password must contain at least one number."),
                code="password_no_number",
            )

    def get_help_text(self):
        return _(
            "Your password must contain at least one uppercase letter and at"
            " least one number."
        )
