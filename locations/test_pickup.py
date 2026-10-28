import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import PickupLocation


class PickupLocationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='pickup-owner')
        self.other = get_user_model().objects.create_user(username='other-owner')
        self.client.force_login(self.user)
        self.url = reverse('locations:pickup_list')
        self.data = {'label': 'Kos Kukusan', 'address': 'Jl. K.H.M. Usman No. 21, Beji, Depok',
                     'latitude': '-6.362100', 'longitude': '106.827900'}
        self.location = PickupLocation.objects.create(owner=self.user, **self.data)

    def write(self, method, url, payload):
        return getattr(self.client, method)(url, json.dumps(payload), content_type='application/json')

    def test_login_is_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.assertEqual(self.write('post', self.url, self.data).status_code, 401)
        self.assertEqual(self.client.get(reverse('locations:saved')).status_code, 302)

    def test_list_only_contains_active_locations_owned_by_account(self):
        PickupLocation.objects.create(owner=self.other, **self.data)
        PickupLocation.objects.create(owner=self.user, is_active=False, **self.data)
        response = self.client.get(self.url)
        self.assertEqual([row['id'] for row in response.json()['locations']], [self.location.pk])
        self.assertIn('no-store', response['Cache-Control'])

    def test_can_save_location_before_registering_an_item(self):
        response = self.write('post', self.url, {**self.data, 'owner': self.other.pk})
        self.assertEqual(response.status_code, 201)
        saved = PickupLocation.objects.get(pk=response.json()['location']['id'])
        self.assertEqual(saved.owner, self.user)
        self.assertEqual(saved.latitude.as_tuple().exponent, -6)

    def test_can_update_own_location(self):
        url = reverse('locations:pickup_detail', args=[self.location.pk])
        response = self.write('patch', url, {**self.data, 'label': 'Titik gerbang', 'latitude': '-6.360123'})
        self.assertEqual(response.status_code, 200)
        self.location.refresh_from_db()
        self.assertEqual(self.location.label, 'Titik gerbang')
        self.assertEqual(str(self.location.latitude), '-6.360123')

    def test_other_accounts_cannot_edit_or_delete_location(self):
        self.client.force_login(self.other)
        url = reverse('locations:pickup_detail', args=[self.location.pk])
        self.assertEqual(self.write('patch', url, self.data).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.location.refresh_from_db()
        self.assertTrue(self.location.is_active)

    def test_delete_hides_location_from_history(self):
        url = reverse('locations:pickup_detail', args=[self.location.pk])
        self.assertEqual(self.client.delete(url).status_code, 200)
        self.location.refresh_from_db()
        self.assertFalse(self.location.is_active)
        self.assertEqual(self.client.get(self.url).json()['locations'], [])
        self.assertEqual(self.write('patch', url, self.data).status_code, 404)

    def test_rejects_invalid_coordinates_and_incomplete_addresses(self):
        for fields in ({'latitude': 91}, {'longitude': -181}, {'latitude': 'NaN'},
                       {'latitude': True}, {'address': ''}, {'label': '<br>'}):
            with self.subTest(fields=fields):
                response = self.write('post', self.url, {**self.data, **fields})
                self.assertEqual(response.status_code, 400)
        self.assertEqual(PickupLocation.objects.count(), 1)

    def test_rejects_malformed_json(self):
        for payload in ('{', '[]', 'null'):
            response = self.client.post(self.url, payload, content_type='application/json')
            self.assertEqual(response.status_code, 400)

    def test_removes_html_from_labels_and_addresses(self):
        response = self.write('post', self.url, {**self.data, 'label': '<b>Kos</b>',
                                               'address': '<div>Jalan Kukusan</div>'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['location']['label'], 'Kos')
        self.assertEqual(response.json()['location']['address'], 'Jalan Kukusan')

    def test_location_writes_require_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse('locations:saved'))
        self.assertEqual(client.post(self.url, json.dumps(self.data), content_type='application/json').status_code, 403)
        response = client.post(self.url, json.dumps(self.data), content_type='application/json',
                               HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 201)

    def test_account_page_does_not_expose_another_accounts_address(self):
        secret = 'Alamat privat pemilik lain'
        PickupLocation.objects.create(owner=self.other, **{**self.data, 'address': secret})
        response = self.client.get(reverse('locations:saved'))
        self.assertContains(response, 'data-manage-only="true"')
        self.assertNotContains(response, secret)
