import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = "admin"
email = "user@gmail.com"  # The email you are trying to use
password = "user123"  # Set a secure password here

# Checks if the user exists; if not, creates a fully privileged admin
if not User.objects.filter(email=email).exists() and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("--- Superuser created successfully! ---")
else:
    print("--- Superuser already exists. ---")