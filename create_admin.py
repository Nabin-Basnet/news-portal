# import os
# import django

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# django.setup()

# from django.contrib.auth import get_user_model

# User = get_user_model()

# email = "user@gmail.com"
# password = "user123"

# # Create admin if it doesn't already exist
# if not User.objects.filter(email=email).exists():
#     User.objects.create_superuser(
#         email=email,
#         password=password
#     )
#     print("--- Superuser created successfully! ---")
# else:
#     print("--- Superuser already exists. ---")