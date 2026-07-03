from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notification

@login_required
def notifications_list(request):
    """View all notifications for the current user."""
    notifications = request.user.notifications.all()
    context = {
        'notifications': notifications
    }
    return render(request, 'notifications/list.html', context)

@login_required
def mark_as_read(request, pk):
    """Mark a specific notification as read."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    # If the notification is tied to an appraisal, redirect to it, else go back to list
    if notification.related_appraisal:
        # Since it's a staff dashboard feature request, redirecting to self appraisal form or my appraisals 
        # is a good fallback. We'll send them to my appraisals or the specific one.
        # But depending on the status, it might be better to just redirect to the list.
        return redirect('appraisals:my_appraisals')
    return redirect('notifications:list')

@login_required
def mark_all_as_read(request):
    """Mark all unread notifications as read."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')
