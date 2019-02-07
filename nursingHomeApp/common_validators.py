from wtforms.validators import ValidationError


def STR_2_NONE(x):
    return x or None


def is_valid_phone(form, field):
    if form.phone.data:
        try:
            int(form.phone.data)
        except ValueError:
            raise ValidationError('Please only include digits in this field')
        if len(form.phone.data) not in {10, 11}:
            raise ValidationError('Phone number must be 10 or 11 digits long')
