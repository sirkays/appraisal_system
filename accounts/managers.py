"""
Custom manager for the CustomUser model.
"""

from django.contrib.auth.models import UserManager


class CustomUserManager(UserManager):
    """Extended user manager for CustomUser."""
    pass
