from django.db.models.signals import post_save
from django.dispatch import receiver

from articles.models import Article
from user.models import User

from .services import send_article_notification


@receiver(post_save, sender=Article)
def notify_users_on_new_article(sender, instance, created, **kwargs):
    if not created:
        return

    emails = list(
        User.objects.filter(
            email_notifications=True
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )

    send_article_notification(instance, emails)