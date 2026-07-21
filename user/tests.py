from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class UserRegistrationTests(APITestCase):
    def test_user_can_register_with_email_and_password(self):
        response = self.client.post(
            '/api/users/',
            {
                'email': 'new.user@example.com',
                'first_name': 'New',
                'last_name': 'User',
                'password': 'SafePassword123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email='new.user@example.com')
        self.assertTrue(user.check_password('SafePassword123!'))
        self.assertNotIn('password', response.data)

    def test_registration_rejects_mismatched_password_confirmation(self):
        response = self.client.post(
            '/api/users/',
            {
                'email': 'new.user@example.com',
                'password': 'SafePassword123!',
                'password2': 'DifferentPassword123!',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_legacy_username_argument_does_not_block_user_creation(self):
        user = get_user_model().objects.create_user(
            email='legacy.client@example.com',
            username='legacy-client',
            password='SafePassword123!',
        )

        self.assertEqual(user.email, 'legacy.client@example.com')
        self.assertTrue(user.check_password('SafePassword123!'))
