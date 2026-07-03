"""
Models for the Notifications app.

Provides the Notification model used to deliver in-app alerts to staff
members regarding appraisal lifecycle events and general announcements
within the State Internal Revenue Service Performance Appraisal System.
"""

from django.db import models


class Notification(models.Model):
    """Represents an in-app notification sent to a staff member."""

    # ------------------------------------------------------------------
    # Notification-type constants
    # ------------------------------------------------------------------
    APPRAISAL_SUBMITTED = 'APPRAISAL_SUBMITTED'
    APPRAISAL_REVIEWED = 'APPRAISAL_REVIEWED'
    APPRAISAL_RETURNED = 'APPRAISAL_RETURNED'
    APPRAISAL_APPROVED = 'APPRAISAL_APPROVED'
    CYCLE_CREATED = 'CYCLE_CREATED'
    CYCLE_ACTIVATED = 'CYCLE_ACTIVATED'
    CYCLE_CLOSED = 'CYCLE_CLOSED'
    GENERAL = 'GENERAL'

    NOTIFICATION_TYPE_CHOICES = [
        (APPRAISAL_SUBMITTED, 'Appraisal Submitted'),
        (APPRAISAL_REVIEWED, 'Appraisal Reviewed'),
        (APPRAISAL_RETURNED, 'Appraisal Returned'),
        (APPRAISAL_APPROVED, 'Appraisal Approved'),
        (CYCLE_CREATED, 'Cycle Created'),
        (CYCLE_ACTIVATED, 'Cycle Activated'),
        (CYCLE_CLOSED, 'Cycle Closed'),
        (GENERAL, 'General'),
    ]

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    recipient = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Recipient',
        help_text='The user who receives this notification.',
    )
    sender = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name='Sender',
        help_text='The user who triggered this notification (if applicable).',
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default=GENERAL,
        verbose_name='Notification Type',
        help_text='The category of this notification.',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Title',
        help_text='A short summary of the notification.',
    )
    message = models.TextField(
        verbose_name='Message',
        help_text='The full notification message body.',
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Read',
        help_text='Whether the recipient has read this notification.',
    )
    related_appraisal = models.ForeignKey(
        'appraisals.Appraisal',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Related Appraisal',
        help_text='The appraisal associated with this notification (if any).',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
    )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.title} → {self.recipient.get_full_name()}"

    def mark_as_read(self) -> None:
        """Mark this notification as read and persist the change."""
        self.is_read = True
        self.save(update_fields=['is_read'])
