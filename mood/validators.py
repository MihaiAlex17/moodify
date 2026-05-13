import re
from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    """
    Parola trebuie sa aiba:
    - Cel putin o litera mare
    - Cel putin o cifra
    - Cel putin un caracter special
    """

    SPECIAL = r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]'

    def validate(self, password, user=None):
        errors = []
        if not re.search(r'[A-Z]', password):
            errors.append('Parola trebuie să conțină cel puțin o literă mare (A-Z).')
        if not re.search(r'[0-9]', password):
            errors.append('Parola trebuie să conțină cel puțin o cifră (0-9).')
        if not re.search(self.SPECIAL, password):
            errors.append('Parola trebuie să conțină cel puțin un caracter special (!@#$%^&* etc.).')
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            'Parola trebuie să conțină cel puțin o literă mare, '
            'o cifră și un caracter special.'
        )
