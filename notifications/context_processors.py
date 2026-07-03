from .models import Notification

def unread_notifications(request):
    """
    Injects unread notifications into the context of all templates
    for authenticated users.
    """
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(is_read=False).order_by('-created_at')
        return {
            'unread_notifications': unread[:5],
            'unread_notifications_count': unread.count()
        }
    return {}
