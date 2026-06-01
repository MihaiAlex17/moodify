import re
from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    """
    Validator custom pentru parola.
    Cere cel putin: o litera mare, o cifra, un caracter special.
    """

    SPECIAL = r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]'

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append('Parola trebuie sa contina cel putin o litera mare (A-Z).')
        if not re.search(r'[0-9]', password):
            errors.append('Parola trebuie sa contina cel putin o cifra (0-9).')
        if not re.search(self.SPECIAL, password):
            errors.append('Parola trebuie sa contina cel putin un caracter special (!@#$%^&* etc.).')
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            'Parola trebuie sa contina cel putin o litera mare, '
            'o cifra si un caracter special.'
        )
