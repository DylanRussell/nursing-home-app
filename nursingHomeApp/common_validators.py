from wtforms.validators import ValidationError


def STR_2_NONE(string):
    """Converts empty string to None, which corresponds to null in mysql"""
    return string or None


def is_valid_phone(form, field):
    """Is the phone number of valid length and contains only digits"""
    if field.data:
        try:
            int(field.data)
        except ValueError:
            raise ValidationError('Please only include digits in this field')
        if len(field.data) not in {10, 11}:
            raise ValidationError('Phone number must be 10 or 11 digits long')

def is_gt_zero(form, field):
    """Raises validation error if field <= 0"""
    if field.data <= 0:
        raise ValidationError('This field must contain a positive integer.')
