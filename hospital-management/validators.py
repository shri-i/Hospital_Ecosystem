"""
validators.py - small form-validation helpers shared by all routes.
Each function returns an error message (string) or None if the value is fine.
"""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

PHONE_RE = re.compile(r'^\d{10}$')


def required(form, fields):
    """Return a list of 'X is required' messages for empty fields."""
    errors = []
    for field, label in fields.items():
        if not form.get(field, '').strip():
            errors.append(f'{label} is required.')
    return errors


def phone_error(value, label='Phone', optional=False):
    value = (value or '').strip()
    if not value and optional:
        return None
    if not PHONE_RE.match(value):
        return f'{label} must be exactly 10 digits.'
    return None


def money_error(value, label):
    try:
        if Decimal(value) < 0:
            return f'{label} cannot be negative.'
    except (InvalidOperation, TypeError):
        return f'{label} must be a number.'
    return None


def int_error(value, label, minimum=0):
    try:
        if int(value) < minimum:
            return f'{label} must be at least {minimum}.'
    except (ValueError, TypeError):
        return f'{label} must be a whole number.'
    return None


def dob_error(value):
    try:
        d = date.fromisoformat(value)
    except (ValueError, TypeError):
        return 'Date of birth is not a valid date.'
    if d > date.today():
        return 'Date of birth cannot be in the future.'
    if d.year < 1900:
        return 'Date of birth looks wrong.'
    return None


def blank_to_none(value):
    """Store empty optional fields as NULL instead of ''."""
    value = (value or '').strip()
    return value or None
