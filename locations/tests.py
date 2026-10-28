import json
from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import GeocodingCache


class CurrentLocationTests(TestCase):
    def setUp(self):
        self.url = reverse('locations:current')
        self.coords = {'latitude': -6.36123, 'longitude': 106.82456}

    def post_location(self, payload=None):
        return self.client.post(
            self.url, data=json.dumps(self.coords if payload is None else payload),
            content_type='application/json',
        )

    @patch('locations.services.requests.get')
    def test_resolves_area_without_exposing_street_address(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {
            'address': {'suburb': 'Beji', 'city': 'Depok', 'road': 'Jalan Rahasia'},
            'display_name': 'Jalan Rahasia, Beji, Depok',
        }
        response = self.post_location()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'label': 'Beji, Depok'})
        params = upstream.call_args.kwargs['params']
        self.assertEqual(params['lat'], '-6.361')
        self.assertEqual(params['lon'], '106.825')
        self.assertEqual(params['zoom'], 13)
        self.assertIn('Pinjemin', upstream.call_args.kwargs['headers']['User-Agent'])
        self.assertIn('no-store', response['Cache-Control'])

    @patch('locations.services.requests.get')
    def test_cached_area_reuses_response(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {'address': {'city': 'Depok'}}
        self.assertEqual(self.post_location().status_code, 200)
        self.assertEqual(self.post_location().json(), {'label': 'Depok'})
        upstream.assert_called_once()

    @patch('locations.services.requests.get')
    def test_invalid_coordinates_never_call_upstream(self, upstream):
        for payload in (
            {}, [], None, {'latitude': 91, 'longitude': 0},
            {'latitude': 0, 'longitude': -181},
            {'latitude': True, 'longitude': 0},
            {'latitude': 'Depok', 'longitude': 0},
            {'latitude': float('nan'), 'longitude': 0},
            {'latitude': 0, 'longitude': float('inf')},
            {'latitude': 10 ** 400, 'longitude': 0},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.url, data=json.dumps(payload), content_type='application/json'
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(
            self.url, data='{broken', content_type='application/json'
        ).status_code, 400)
        upstream.assert_not_called()

    @patch('locations.services.requests.get')
    def test_global_quota_applies_to_different_clients(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {'address': {'city': 'Depok'}}
        self.assertEqual(self.post_location().status_code, 200)
        response = Client().post(
            self.url, data=json.dumps({'latitude': -6.4, 'longitude': 106.8}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 429)
        self.assertGreaterEqual(int(response['Retry-After']), 1)
        upstream.assert_called_once()

    @patch('locations.services.requests.get')
    def test_quota_reopens_after_cooldown(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {'address': {'city': 'Depok'}}
        self.assertEqual(self.post_location().status_code, 200)
        GeocodingCache.objects.filter(key__startswith='quota:').update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.post_location(
            {'latitude': -6.4, 'longitude': 106.8}
        ).status_code, 200)
        self.assertEqual(upstream.call_count, 2)

    @patch('locations.services.requests.get')
    def test_expired_cached_result_is_refreshed(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {'address': {'city': 'Depok'}}
        self.post_location()
        GeocodingCache.objects.all().update(expires_at=timezone.now() - timedelta(seconds=1))
        upstream.return_value.json.return_value = {'address': {'city': 'Jakarta'}}
        self.assertEqual(self.post_location().json(), {'label': 'Jakarta'})

    @patch('locations.services.requests.get', side_effect=requests.Timeout)
    def test_upstream_timeout_returns_recoverable_error(self, upstream):
        response = self.post_location()
        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.json())
        self.assertFalse(GeocodingCache.objects.filter(key__startswith='result:').exists())

    @patch('locations.services.requests.get')
    def test_upstream_rate_limit_is_shared_with_subsequent_requests(self, upstream):
        upstream.return_value = Mock(status_code=429, headers={'Retry-After': '60'})
        response = self.post_location()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '60')
        self.assertEqual(self.post_location(
            {'latitude': -6.4, 'longitude': 106.8}
        ).status_code, 429)
        upstream.assert_called_once()

    @patch('locations.services.requests.get')
    def test_unknown_area_and_malformed_provider_responses(self, upstream):
        cases = [
            (200, {'error': 'Unable to geocode'}, 404),
            (200, {'address': None}, 404),
            (200, ['unexpected'], 404),
            (200, {'address': {'road': 'Jalan Rahasia'}}, 404),
            (404, {}, 404),
            (500, {}, 503),
        ]
        for status, payload, expected in cases:
            with self.subTest(status=status, payload=payload):
                GeocodingCache.objects.all().delete()
                upstream.return_value = Mock(status_code=status)
                upstream.return_value.json.return_value = payload
                self.assertEqual(self.post_location().status_code, expected)

    @patch('locations.services.requests.get')
    def test_invalid_json_from_provider_returns_error(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.side_effect = ValueError('invalid JSON')
        self.assertEqual(self.post_location().status_code, 503)

    @patch('locations.services.requests.get')
    def test_get_and_missing_csrf_cannot_call_provider(self, upstream):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(
            self.url, data=json.dumps(self.coords), content_type='application/json'
        ).status_code, 403)
        upstream.assert_not_called()

    @patch('locations.services.requests.get')
    def test_home_has_picker_and_allows_csrf_protected_location_request(self, upstream):
        upstream.return_value = Mock(status_code=200)
        upstream.return_value.json.return_value = {'address': {'city': 'Depok'}}
        client = Client(enforce_csrf_checks=True)
        home = client.get(reverse('home'))
        self.assertContains(home, 'data-location-widget')
        self.assertContains(home, 'js/location.js')
        self.assertContains(home, 'OpenStreetMap contributors')
        upstream.assert_not_called()
        response = client.post(
            self.url, data=json.dumps(self.coords), content_type='application/json',
            HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value,
        )
        self.assertEqual(response.status_code, 200)
