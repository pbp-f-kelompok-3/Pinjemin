from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from barang.models import Barang, Lokasi
from categories.models import Category

from .models import PickupLocation


class LocationApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user(username='location-owner')
        cls.other = users.create_user(username='another-owner')
        cls.pickup = {
            'label': 'Kos Kukusan',
            'address': 'Jalan K.H.M. Usman',
            'latitude': -6.361543,
            'longitude': 106.827812,
        }
        cls.other_pickup = PickupLocation.objects.create(owner=cls.other, **cls.pickup)

    def test_crud_uses_session_and_csrf_and_is_visible_on_the_web(self):
        url = reverse('locations_api:pickup_list')
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.get(url).status_code, 403)
        client.force_login(self.owner)
        client.get(reverse('accounts:api_me'))
        self.assertEqual(client.post(url, self.pickup, format='json').status_code, 403)
        client.credentials(HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)

        response = client.post(url, self.pickup, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        location = response.json()
        self.assertEqual(location['latitude'], self.pickup['latitude'])
        self.assertEqual(client.get(url).json(), [location])
        detail = reverse('locations_api:pickup_detail', args=[location['id']])
        edited = client.patch(detail, {'label': 'Gerbang Kukusan'}, format='json')
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(edited.json()['address'], self.pickup['address'])
        web_locations = client.get(reverse('locations:pickup_list')).json()['locations']
        self.assertEqual(web_locations, [edited.json()])

        self.assertEqual(client.delete(detail).status_code, 204)
        self.assertFalse(PickupLocation.objects.get(pk=location['id']).is_active)
        self.assertEqual(client.get(url).json(), [])
        self.assertEqual(client.patch(detail, self.pickup, format='json').status_code, 404)

    def test_location_writes_reject_invalid_inputs_and_other_accounts(self):
        self.client.force_login(self.owner)
        url = reverse('locations_api:pickup_list')
        for changes in ({'longitude': 181}, {'latitude': 'NaN'}, {'label': '<b></b>'}):
            with self.subTest(changes=changes):
                response = self.client.post(url, {**self.pickup, **changes}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
        detail = reverse('locations_api:pickup_detail', args=[self.other_pickup.pk])
        self.assertEqual(self.client.patch(detail, {'label': 'Changed'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(detail).status_code, 404)
        self.assertEqual(PickupLocation.objects.count(), 1)

    def test_nearby_uses_catalogue_data_and_returns_approximate_pins(self):
        category = Category.objects.create(name='Uji lokasi mobile')
        point = Lokasi.objects.create(
            owner=self.owner, nama_area='Kukusan', short_label='Kukusan',
            patokan='Alamat privat', latitude='-6.361543', longitude='106.827812',
        )
        item = Barang.objects.create(
            pemilik=self.owner, nama_barang='Kabel rol', kategori=category,
            lokasi=point, jenis_penawaran='gratis', status_penawaran='aktif',
            deskripsi='Kabel rol untuk acara kampus.', foto_utama='barang/fotos/kabel-rol.jpg',
        )
        url = reverse('locations_api:nearby')
        query = {'latitude': -6.3621, 'longitude': 106.8279, 'radius': 2}
        response = self.client.get(url, query)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.json()['radius_km'], 2)
        pin, = response.json()['items']
        self.assertEqual(pin['id'], item.pk)
        self.assertEqual(pin['latitude'], -6.362)
        self.assertTrue(pin['is_approximate'])
        self.assertNotIn('address', pin)
        self.assertEqual(self.client.get(url, {**query, 'radius': 3}).status_code, 400)
        self.assertEqual(self.client.get(url, {**query, 'latitude': 'NaN'}).status_code, 400)
