"""
Models for the Departments app.

Defines the Department entity used across the Staff Performance
Appraisal System for the State Internal Revenue Service.
"""

from django.db import models


class Department(models.Model):
    """
    Represents an organisational department within the
    State Internal Revenue Service (e.g. Tax, Audit, HR).
    """

    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Full name of the department.",
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short unique code for the department (e.g. 'TAX', 'AUDIT', 'HR').",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the department's responsibilities.",
    )
    hod = models.OneToOneField(
        "accounts.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_department",
        limit_choices_to={"role": "HOD"},
        verbose_name="Head of Department",
        help_text="The user designated as Head of Department.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def staff_count(self) -> int:
        """Return the number of staff members assigned to this department."""
        return self.staff_members.count()

    # ------------------------------------------------------------------
    # Dunder / Meta
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"
