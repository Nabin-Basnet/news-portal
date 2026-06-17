from django.conf import settings
from django.core.mail import send_mail

from user.models import User


def send_article_notification(article):

    recipients = list(
        User.objects.filter(
            email_notifications=True
        )
        .exclude(email="")
        .values_list(
            "email",
            flat=True
        )
    )

    if not recipients:
        return


    subject = f"New Article Published: {article.title}"


    message = f"""
Hello,

A new article has been published on News Portal.

Title:
{article.title}


Summary:
{article.summary}


Author:
{article.author_name}


Visit the website to read the complete article.

Thank you.
"""


    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=False,
    )