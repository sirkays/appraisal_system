"""
Custom user model for the Staff Performance Appraisal System.

Extends Django's ``AbstractUser`` to add fields specific to the
State Internal Revenue Service organisational structure, including
a unique staff identifier, role-based access designation, department
association, and supervisor hierarchy.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import CustomUserManager


class CustomUser(AbstractUser):
    """
    Staff member in the State Internal Revenue Service.

    Roles
    -----
    * **STAFF** – regular employee subject to appraisal.
    * **SUPERVISOR** – direct line manager who appraises staff.
    * **HOD** – Head of Department with departmental oversight.
    * **HR_ADMIN** – Human Resources administrator with system-wide access.
    """

    # ------------------------------------------------------------------
    # Role constants & choices
    # ------------------------------------------------------------------
    STAFF = "STAFF"
    SUPERVISOR = "SUPERVISOR"
    HOD = "HOD"
    HR_ADMIN = "HR_ADMIN"

    ROLE_CHOICES = [
        (STAFF, "Staff"),
        (SUPERVISOR, "Supervisor"),
        (HOD, "Head of Department"),
        (HR_ADMIN, "HR Administrator"),
    ]

    # ------------------------------------------------------------------
    # Additional fields
    # ------------------------------------------------------------------
    staff_id = models.CharField(
        "Staff ID",
        max_length=20,
        unique=True,
        help_text="Unique staff identifier (e.g. STF-00001).",
    )
    role = models.CharField(
        "Role",
        max_length=20,
        choices=ROLE_CHOICES,
        default=STAFF,
        help_text="Organisational role that determines access permissions.",
    )
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
        verbose_name="Department",
        help_text="Department to which this staff member belongs.",
    )
    designation = models.CharField(
        "Designation",
        max_length=100,
        blank=True,
        help_text="Job title or designation within the organisation.",
    )
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        verbose_name="Supervisor",
        help_text="Direct supervisor responsible for appraising this staff member.",
    )
    phone = models.CharField(
        "Phone Number",
        max_length=20,
        blank=True,
        help_text="Contact phone number.",
    )
    profile_picture = models.FileField(
        "Profile Picture",
        upload_to="profile_pics/",
        blank=True,
        null=True,
        help_text="Optional profile photograph.",
    )

    objects = CustomUserManager()

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def is_staff_role(self) -> bool:
        """Return ``True`` if this user holds the regular STAFF role."""
        return self.role == self.STAFF

    @property
    def is_supervisor(self) -> bool:
        """Return ``True`` if this user holds the SUPERVISOR role."""
        return self.role == self.SUPERVISOR

    @property
    def is_hod(self) -> bool:
        """Return ``True`` if this user holds the HOD role."""
        return self.role == self.HOD

    @property
    def is_hr_admin(self) -> bool:
        """Return ``True`` if this user holds the HR_ADMIN role."""
        return self.role == self.HR_ADMIN

    @property
    def full_name(self) -> str:
        """Return the user's full name, falling back to the username."""
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.staff_id:
            self.staff_id = f"STF-{self.pk:05d}"
            super().save(update_fields=["staff_id"])

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.full_name} ({self.staff_id})"

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"
