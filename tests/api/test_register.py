from django.test.utils import override_settings
from rest_framework import status

from rest_registration.api.views import register, verify_registration
from rest_registration.api.views.register import RegisterSigner
from rest_registration.settings import registration_settings
from .base import APIViewTestCase


REGISTER_VERIFICATION_URL = '/verify-account/'


class RegisterViewTestCase(APIViewTestCase):

    def test_register_serializer_ok(self):
        serializer_class = registration_settings.REGISTER_SERIALIZER_CLASS
        serializer = serializer_class(data={})
        field_names = {f for f in serializer.get_fields()}
        self.assertEqual(
            field_names,
            {'username', 'first_name', 'last_name', 'email',
             'password', 'password_confirm'},
        )

    @override_settings(
        REST_REGISTRATION={
            'REGISTER_VERIFICATION_URL': REGISTER_VERIFICATION_URL,
        }
    )
    def test_register_ok(self):
        username = 'testusername'
        password = 'testpassword'
        request = self.factory.post('', {
            'username': username,
            'password': password,
            'password_confirm': password,
        })
        with self.assert_mail_sent():
            response = register(request)
        self.assert_valid_response(response, status.HTTP_201_CREATED)
        user_id = response.data['id']
        user = self.user_class.objects.get(id=user_id)
        self.assertEqual(user.username, username)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_active)

    def test_register_not_matching_password(self):
        username = 'testusername'
        password = 'testpassword'
        request = self.factory.post('', {
            'username': username,
            'password': password,
            'password_confirm': 'blah',
        })
        with self.assert_no_mail_sent():
            response = register(request)
        self.assert_invalid_response(response, status.HTTP_400_BAD_REQUEST)


class VerifyRegistrationViewTestCase(APIViewTestCase):

    @override_settings(
        REST_REGISTRATION={
            'REGISTER_VERIFICATION_URL': REGISTER_VERIFICATION_URL,
        }
    )
    def test_verify_ok(self):
        user = self.create_test_user(is_active=False)
        self.assertFalse(user.is_active)
        signer = RegisterSigner({'user_id': user.pk})
        data = signer.get_signed_data()
        request = self.factory.post('', data)
        response = verify_registration(request)
        self.assert_valid_response(response, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
