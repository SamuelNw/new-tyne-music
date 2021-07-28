from django.test import tag
from django.shortcuts import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token

from core.views import CREATE_USER, EDIT_USER, GET_USER
from core.models import User
from core.serializers import UserSerializer
from core.forms import CoreUserCreationForm, CoreUserEditForm


# noinspection PyPep8Naming
@tag('core-v-a')
class AccountActionTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='view_user',
            email='email@test.com',
            password='pass@123'
        )
        self.def_resp = {
            'url': 'account action',

        }

    def test_unknown_action(self):
        NOT_AN_ACTION = 'not_an_action'
        self.def_resp.update({
            "404 Error": f"{NOT_AN_ACTION} not supported",
            "urls_supported": [
                "/core/accounts/create/",
                "/core/accounts/edit/",
                "/core/accounts/get/?username=user"
            ]
        })
        response = self.client.get(reverse('core:account-action', kwargs={'action': NOT_AN_ACTION}))
        self.assertEqual(response.status_code, 404)
        self.assertDictEqual(response.json(), self.def_resp)

    @tag('core-v-a-gu')
    def test_get_user(self):
        url = f"{reverse('core:account-action', kwargs={'action': GET_USER})}?username={self.user.username}"
        user_info = UserSerializer(self.user).data
        profiles = user_info.pop('profiles')
        self.def_resp.update({
            "action": "Retrieve user",
            "user": user_info
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.def_resp)

        self.client.force_login(user=self.user)
        response = self.client.get(url)
        user_info.update({
            'profiles': profiles
        })
        self.def_resp.update({
            'user': user_info
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.def_resp)

    def test_create_user_get(self):
        url = reverse('core:account-action', kwargs={'action': CREATE_USER})

        self.def_resp.update({
            "action": "Create a new user",
            'login_required': False,
            "fields": CoreUserCreationForm().fields_info()
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), self.def_resp)

    def test_create_user_post(self):
        url = reverse('core:account-action', kwargs={'action': CREATE_USER})
        # POST data with errors
        data = {
            'username': self.user.username,
            'email': 'test@email.com',
            'password': 'pass@123',
            'password_2': 'pass@123'
        }
        self.def_resp.update(dict(
            errors={
                'username': [f'The username \'{self.user.username}\' already exists'],
            },
            success=False,
            action='Create user'
        ))
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 202)
        self.assertDictEqual(response.json(), self.def_resp)

        # correct data
        data.update({
            'username': 'abs_new_username'
        })
        self.def_resp.update(dict(
            success=True,
        ))
        self.def_resp.pop('errors')
        response = self.client.post(url, data=data)
        user = User.objects.get(username='abs_new_username')
        token = Token.objects.get(user=user)
        self.def_resp.update({
            'new_user': UserSerializer(user).data,
            'user_token': token.key
        })
        self.assertEqual(response.status_code, 201)
        self.assertDictEqual(response.json(), self.def_resp)

    def test_edit_user_get(self):
        url = reverse('core:account-action', kwargs={'action': EDIT_USER})

        self.def_resp.update({
            'action': 'Edit an existing user',
            'login_required': True,
            'fields': CoreUserEditForm(user=None).fields_info()
        })

        response = self.client.get(url)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), self.def_resp)


@tag('core-v-l')
class LoginTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self._pass = 'pass@123'
        self.user = User.objects.create_user(
            username='login_user',
            email='email@test.com',
            password=self._pass
        )
        self.def_resp = {
            'url': 'user authentication',
        }
        self.url = reverse('core:login')

    def test_login_get(self):
        self.def_resp.update({
            'fields': ['username', 'email', 'password'],
            'returns': ['token', 'user_data']
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), self.def_resp)

    def test_login_post_wrong_data(self):
        self.def_resp.update({
            'success': False,
            'error': 'Wrong Credentials'
        })
        response = self.client.post(self.url, data={
            'username': self.user.username,
            'password': 'wrong_password'
        })
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), self.def_resp)

    def test_login_with_username_or_email(self):
        self.def_resp.update({
            'success': True,
            'token': self.user.get_user_auth_token().key,
            'details': UserSerializer(self.user).data
        })

        # login with username
        response = self.client.post(self.url, data={
            'username': self.user.username,
            'password': self._pass
        })
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), self.def_resp)

        # login with email
        response = self.client.post(self.url, data={
            'email': self.user.email,
            'password': self._pass
        })
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), self.def_resp)

        # login with email and username
        response = self.client.post(self.url, data={
            'username': self.user.username,
            'email': self.user.email,
            'password': self._pass
        })
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(response.json(), self.def_resp)
