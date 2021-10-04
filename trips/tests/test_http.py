import base64
import json
from inspect import signature
from re import U
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from trips.serializers import UserSerializer, TripSerializer
from trips.models import Trip


USERNAME = 'user@example.com'
PASSWORD = 'pAssw0rd!'

def create_user(username=USERNAME, password=PASSWORD, group_name='rider'): 
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(username=username, password=password)
    user.groups.add(group)
    user.save()
    return user

class AuthenticationTest(APITestCase):
    def test_user_can_sign_up(self):
        response = self.client.post(reverse('sign_up'), data={
            'username': USERNAME,
            'first_name': 'Test',
            'last_name': 'User',
            'password1': PASSWORD,
            'password2': PASSWORD,
            'group': 'rider'
        })

        user = get_user_model().objects.last()                  # 테스트 서버에 등록된 가장 최신 데이터 하나를 가져옴
        self.assertEqual(status.HTTP_201_CREATED, response.status_code) # POST 요청이므로 201, response.status_code 역시 동일
        self.assertEqual(response.data['id'], user.id)                # 서버 -> client에서 주는 response의 data안의 key값과 user 객체의 
        self.assertEqual(response.data['username'], user.username)
        self.assertEqual(response.data['first_name'], user.first_name)
        self.assertEqual(response.data['last_name'], user.last_name)
        self.assertEqual(response.data['group'], user.group)


    def test_user_can_log_in(self):
        user = create_user()
        response = self.client.post(reverse('log_in'), data={
            'username': USERNAME,
            'password': PASSWORD
        })

        # Parse payload data from access token
        access = response.data['access']
        header, payload, signature = access.split('.')
        decoded_payload = base64.b64decode(f'{payload}==')
        payload_data = json.loads(decoded_payload)

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertIsNotNone(response.data['refresh'])
        self.assertEqual(payload_data['id'], user.id)
        self.assertEqual(payload_data['username'], user.username)
        self.assertEqual(payload_data['first_name'], user.first_name)
        self.assertEqual(payload_data['last_name'], user.last_name)
        
        
class HttpTripTest(APITestCase):
    def setUp(self):
        self.user = create_user() # changed
        self.client.login(username=self.user.username, password=PASSWORD)  # changed

    def test_user_can_list_trips(self): # changed
        trips = [
            Trip.objects.create(
                pick_up_address='A', drop_off_address='B', rider=self.user),
            Trip.objects.create(
                pick_up_address='B', drop_off_address='C', rider=self.user),
            Trip.objects.create(
                pick_up_address='C', drop_off_address='D')
        ]
        response = self.client.get(reverse('trips:trip_list'))
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        exp_trip_ids = [str(trip.id) for trip in trips[0:2]]
        act_trip_ids = [trip.get('id') for trip in response.data]
        self.assertCountEqual(act_trip_ids, exp_trip_ids)

    def test_user_can_retrieve_trip_by_id(self): # changed
        trip = Trip.objects.create(
            pick_up_address='A', drop_off_address='B', rider=self.user)
        response = self.client.get(trip.get_absolute_url())
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(str(trip.id), response.data.get('id'))