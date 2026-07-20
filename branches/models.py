"""
Models for the Branches app.

Defines the Branch entity used to group users and departments
by organizational location within the Staff Appraisal Organization.
"""

from django.conf import settings
from django.db import models


class Branch(models.Model):
    """
    Represents an organizational branch/location within the
    Staff Appraisal Organization (e.g. 'Headquarters', 'Zonal Office Ikeja').
    
    Users and departments can belong to multiple branches.
    Appraisal cycles are scoped to a specific branch.
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Full name of the branch.",
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short unique code for the branch (e.g. 'HQ', 'ZO-IKJ').",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the branch location or purpose.",
    )
    departments = models.ManyToManyField(
        'departments.Department',
        blank=True,
        related_name='branches',
        help_text="Departments that operate within this branch.",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='branches',
        help_text="Staff members assigned to this branch.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def member_count(self) -> int:
        """Return the number of staff members in this branch."""
        return self.members.count()

    @property
    def department_count(self) -> int:
        """Return the number of departments in this branch."""
        return self.departments.count()

    # ------------------------------------------------------------------
    # Dunder / Meta
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
