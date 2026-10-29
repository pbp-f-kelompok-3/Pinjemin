from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

from locations.models import PickupLocation
from .forms import BarangForm
from categories.models import Category
from .models import Barang, Lokasi
from .services import save_item_with_pickup
from .tests import generate_test_image


class ItemPickupTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = TemporaryDirectory()
        cls.addClassCleanup(cls.media.cleanup)
        cls.storage = override_settings(MEDIA_ROOT=cls.media.name)
        cls.storage.enable()
        cls.addClassCleanup(cls.storage.disable)

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='item-pickup-owner')
        self.other = get_user_model().objects.create_user(username='other-item-owner')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='Pakaian')
        self.location = PickupLocation.objects.create(owner=self.user, label='Kos Kukusan',
            address='Jl. K.H.M. Usman No. 21, Beji, Depok', latitude='-6.362100', longitude='106.827900')
        self.data = {'nama_barang': 'Jas sidang hitam', 'deskripsi': 'Jas ukuran L, bersih dan lengkap.',
                     'kategori': self.category.pk, 'jenis_penawaran': 'sewa', 'tarif_per_hari': 25000,
                     'pickup_mode': 'saved', 'pickup_location': self.location.pk,
                     'pickup_latitude': '-6.361500', 'pickup_longitude': '106.828600'}

    def post_item(self, **changes):
        return self.client.post(reverse('barang:tambah'),
            {**self.data, **changes, 'foto_utama': generate_test_image()})

    def test_selected_point_is_saved_as_an_independent_item_location(self):
        response = self.post_item()
        self.assertRedirects(response, reverse('barang:dashboard'))
        item = Barang.objects.get()
        self.assertTrue(item.lokasi.is_pickup_snapshot)
        self.assertEqual(item.lokasi.owner, self.user)
        self.assertEqual(item.lokasi.full_address, self.location.address)
        self.assertEqual(item.lokasi.latitude, Decimal('-6.361500'))
        self.assertEqual(item.lokasi.longitude, Decimal('106.828600'))
        self.location.refresh_from_db()
        self.assertEqual(self.location.latitude, Decimal('-6.362100'))

    def test_editing_or_removing_history_does_not_change_an_item(self):
        self.post_item()
        self.location.label = 'Label baru'
        self.location.address = 'Alamat baru'
        self.location.latitude = '-6.370000'
        self.location.is_active = False
        self.location.save()
        item = Barang.objects.get()
        self.assertEqual(item.lokasi.nama_area, 'Kos Kukusan')
        self.assertEqual(item.lokasi.full_address, 'Jl. K.H.M. Usman No. 21, Beji, Depok')
        self.assertEqual(item.lokasi.latitude, Decimal('-6.361500'))

    def test_cannot_choose_another_users_or_deleted_history(self):
        for owner, active in ((self.other, True), (self.user, False)):
            source = PickupLocation.objects.create(owner=owner, label='Private', address='Secret',
                latitude=0, longitude=0, is_active=active)
            response = self.post_item(pickup_location=source.pk)
            self.assertEqual(response.status_code, 200)
            self.assertIn('pickup_location', response.context['form'].errors)
        self.assertFalse(Barang.objects.exists())
        self.assertFalse(Lokasi.objects.exists())

    def test_invalid_item_does_not_leave_a_location_snapshot(self):
        response = self.post_item(nama_barang='')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Barang.objects.exists())
        self.assertFalse(Lokasi.objects.exists())
        self.assertTrue(PickupLocation.objects.filter(pk=self.location.pk).exists())

    def test_rejects_out_of_range_or_incomplete_points(self):
        for fields in ({'pickup_latitude': '91'}, {'pickup_longitude': ''}):
            with self.subTest(fields=fields):
                response = self.post_item(**fields)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertFalse(Barang.objects.exists())

    def test_cannot_bypass_picker_by_posting_new_mode_without_saved_location(self):
        response = self.post_item(pickup_mode='new', pickup_location='')
        self.assertIn('pickup_location', response.context['form'].errors)
        self.assertFalse(Barang.objects.exists())

    def test_history_point_is_used_if_no_override_is_posted(self):
        self.post_item(pickup_latitude='', pickup_longitude='')
        self.assertEqual(Barang.objects.get().lokasi.latitude, Decimal(self.location.latitude))

    def test_snapshot_is_rolled_back_if_saving_item_fails(self):
        form = BarangForm(self.data, {'foto_utama': generate_test_image()}, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        with patch('barang.models.Barang.save', side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):
                save_item_with_pickup(form, self.user)
        self.assertFalse(Lokasi.objects.exists())

    def test_other_users_cannot_reuse_private_item_snapshots_through_legacy_field(self):
        self.post_item()
        snapshot = Barang.objects.get().lokasi_id
        self.client.force_login(self.other)
        response = self.post_item(pickup_location='', pickup_mode='', lokasi=snapshot)
        self.assertIn('lokasi', response.context['form'].errors)
        self.assertEqual(Barang.objects.count(), 1)

    def test_editing_an_existing_item_keeps_its_pickup_snapshot(self):
        self.post_item()
        item = Barang.objects.get()
        location_id = item.lokasi_id
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            'nama_barang': item.nama_barang, 'deskripsi': 'Deskripsi diperbarui',
            'kategori': self.category.pk, 'jenis_penawaran': 'sewa', 'tarif_per_hari': 30000,
            'lokasi': location_id, 'status_penawaran': 'aktif'})
        self.assertRedirects(response, reverse('barang:dashboard'))
        item.refresh_from_db()
        self.assertEqual(item.lokasi_id, location_id)
        self.assertEqual(item.deskripsi, 'Deskripsi diperbarui')

    def test_picker_page_only_embeds_own_history(self):
        PickupLocation.objects.create(owner=self.other, label='Secret label', address='Secret address',
            latitude=0, longitude=0)
        response = self.client.get(reverse('barang:tambah'))
        self.assertContains(response, 'Lokasi penjemputan')
        self.assertNotContains(response, 'Secret address')
        self.assertEqual(response.context['pickup_locations_data'][0]['id'], self.location.pk)

    def test_photo_size_is_enforced_on_server(self):
        photo = generate_test_image()
        photo.size = 5 * 1024 * 1024 + 1
        form = BarangForm(self.data, {'foto_utama': photo}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('foto_utama', form.errors)

    def edit_fixture(self):
        self.post_item()
        item = Barang.objects.select_related('lokasi').get()
        data = {'nama_barang': item.nama_barang, 'deskripsi': 'Deskripsi diperbarui',
                'kategori': item.kategori_id, 'jenis_penawaran': 'sewa', 'tarif_per_hari': 25000,
                'status_penawaran': 'aktif', 'lokasi': item.lokasi_id, 'pickup_mode': 'current',
                'pickup_latitude': str(item.lokasi.latitude),
                'pickup_longitude': str(item.lokasi.longitude)}
        return item, data

    def test_edit_map_starts_with_item_snapshot_even_after_history_is_deleted(self):
        item, _ = self.edit_fixture()
        self.location.is_active = False
        self.location.save()
        response = self.client.get(reverse('barang:edit', args=[item.pk]))
        self.assertContains(response, 'data-pickup-map')
        self.assertContains(response, 'Lokasi saat ini')
        self.assertEqual(response.context['pickup_locations_data'], [])
        self.assertEqual(response.context['pickup_current_data']['latitude'], -6.3615)
        self.assertEqual(response.context['form']['pickup_mode'].value(), 'current')
        self.assertEqual(response.context['form']['pickup_latitude'].value(), Decimal('-6.361500'))

    def test_edit_current_mode_keeps_location_and_photo_without_new_snapshot(self):
        item, data = self.edit_fixture()
        original_location, original_photo = item.lokasi_id, item.foto_utama.name
        self.location.delete()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), data)
        self.assertRedirects(response, reverse('barang:dashboard'))
        item.refresh_from_db()
        self.assertEqual(item.lokasi_id, original_location)
        self.assertEqual(item.foto_utama.name, original_photo)
        self.assertEqual(Lokasi.objects.count(), 1)
        self.assertFalse(PickupLocation.objects.exists())

    def test_moving_current_pin_only_changes_this_items_snapshot(self):
        item, data = self.edit_fixture()
        original_location, original_photo = item.lokasi_id, item.foto_utama.name
        another = Barang.objects.create(pemilik=self.user, nama_barang='Barang kedua',
            foto_utama=original_photo, deskripsi='Masih menggunakan titik lama', kategori=self.category,
            jenis_penawaran='gratis', tarif_per_hari=0, lokasi=item.lokasi)
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_latitude': '-6.363222', 'pickup_longitude': '106.829111'})
        self.assertRedirects(response, reverse('barang:dashboard'))
        item.refresh_from_db()
        another.refresh_from_db()
        self.location.refresh_from_db()
        self.assertNotEqual(item.lokasi_id, original_location)
        self.assertEqual(item.lokasi.latitude, Decimal('-6.363222'))
        self.assertEqual(item.lokasi.full_address, self.location.address)
        self.assertEqual(item.foto_utama.name, original_photo)
        self.assertEqual(another.lokasi_id, original_location)
        self.assertEqual(another.lokasi.latitude, Decimal('-6.361500'))
        self.assertEqual(self.location.latitude, Decimal('-6.362100'))

    def test_legacy_location_can_be_kept_without_inventing_a_point_or_given_a_new_point(self):
        item, data = self.edit_fixture()
        legacy = Lokasi.objects.create(nama_area='Barel UI', short_label='Barel', patokan='Dekat Kober')
        item.lokasi = legacy
        item.save()
        url = reverse('barang:edit', args=[item.pk])
        response = self.client.get(url)
        self.assertIsNone(response.context['pickup_current_data']['latitude'])
        post_data = {**data, 'lokasi': legacy.pk, 'pickup_latitude': '', 'pickup_longitude': ''}
        self.assertEqual(self.client.post(url, post_data).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.lokasi_id, legacy.pk)
        self.assertIsNone(item.lokasi.latitude)
        self.assertEqual(self.client.post(url, {**post_data, 'pickup_latitude': '-6.361000',
                                               'pickup_longitude': '106.828000'}).status_code, 302)
        item.refresh_from_db()
        legacy.refresh_from_db()
        self.assertNotEqual(item.lokasi_id, legacy.pk)
        self.assertEqual(item.lokasi.owner, self.user)
        self.assertIsNone(legacy.latitude)

    def test_invalid_current_point_does_not_change_item_and_preserves_bound_form(self):
        item, data = self.edit_fixture()
        for changes in ({'pickup_latitude': '91'}, {'pickup_longitude': ''}):
            response = self.client.post(reverse('barang:edit', args=[item.pk]), {**data, **changes})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertEqual(response.context['pickup_current_data']['latitude'], -6.3615)
            for field, value in changes.items():
                self.assertEqual(response.context['form'][field].value(), value)
        item.refresh_from_db()
        self.assertEqual(item.lokasi.latitude, Decimal('-6.361500'))
        self.assertEqual(Lokasi.objects.count(), 1)

    def test_edit_can_choose_history_instead_of_current_point(self):
        item, data = self.edit_fixture()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': 'saved', 'pickup_location': self.location.pk,
            'pickup_latitude': '', 'pickup_longitude': ''})
        self.assertRedirects(response, reverse('barang:dashboard'))
        item.refresh_from_db()
        self.assertEqual(item.lokasi.latitude, Decimal('-6.362100'))
        self.assertNotEqual(item.lokasi_id, data['lokasi'])

    def test_edit_rejects_another_accounts_history(self):
        item, data = self.edit_fixture()
        source = PickupLocation.objects.create(owner=self.other, label='Private', address='Secret',
            latitude=0, longitude=0)
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': 'saved', 'pickup_location': source.pk})
        self.assertIn('pickup_location', response.context['form'].errors)
        self.assertNotContains(response, 'Secret')
        item.refresh_from_db()
        self.assertEqual(item.lokasi_id, data['lokasi'])

    def test_current_mode_cannot_be_used_to_create_an_item_without_a_location(self):
        response = self.post_item(pickup_mode='current', pickup_location='')
        self.assertIn('pickup_location', response.context['form'].errors)
        self.assertFalse(Barang.objects.exists())

    def test_edit_rejects_unsaved_new_location_instead_of_silently_using_old_point(self):
        item, data = self.edit_fixture()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': 'new', 'pickup_location': '',
            'pickup_latitude': '', 'pickup_longitude': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('pickup_location', response.context['form'].errors)
        item.refresh_from_db()
        self.assertEqual(item.deskripsi, 'Jas ukuran L, bersih dan lengkap.')

    def test_edit_requires_a_selection_when_history_mode_is_submitted(self):
        item, data = self.edit_fixture()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': 'saved', 'pickup_location': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('pickup_location', response.context['form'].errors)

    def test_legacy_edit_accepts_zero_coordinates_without_replacing_them(self):
        item, data = self.edit_fixture()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': '', 'pickup_latitude': '0', 'pickup_longitude': '0'})
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.lokasi.latitude, Decimal('0'))
        self.assertEqual(item.lokasi.longitude, Decimal('0'))

    def test_legacy_edit_rejects_incomplete_coordinates(self):
        item, data = self.edit_fixture()
        response = self.client.post(reverse('barang:edit', args=[item.pk]), {
            **data, 'pickup_mode': '', 'pickup_latitude': '', 'pickup_longitude': '106.830000'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('pickup_location', response.context['form'].errors)

    def test_detail_shows_map_with_json_coordinates_even_at_zero_for_owner(self):
        self.post_item(pickup_latitude='0', pickup_longitude='0')
        item = Barang.objects.get()
        with override_settings(OSM_TILE_URL='https://example.test/{z}/{x}/{y}.png'):
            response = self.client.get(reverse('barang:detail', args=[item.pk]))
        self.assertContains(response, 'data-pickup-detail-map')
        self.assertContains(response, 'https://www.google.com/maps/search/?api=1&amp;query=0.000000,0.000000')
        self.assertEqual(response.context['pickup_detail_data']['latitude'], 0)
        self.assertEqual(response.context['pickup_detail_data']['tileUrl'],
                         'https://example.test/{z}/{x}/{y}.png')

    def test_detail_does_not_disclose_exact_address_or_coordinates_to_visitors(self):
        self.post_item()
        item = Barang.objects.get()
        for user in (None, self.other):
            if user is None:
                self.client.logout()
            else:
                self.client.force_login(user)
            response = self.client.get(reverse('barang:detail', args=[item.pk]))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, item.lokasi.full_address)
            self.assertNotContains(response, 'pickup-detail-data')
            self.assertNotContains(response, str(item.lokasi.latitude))
            self.assertNotContains(response, 'maps?q=')
            self.assertNotContains(response, 'www.google.com/maps/search/')

    def test_google_maps_link_uses_coordinates_with_decimal_points_in_indonesian_locale(self):
        self.post_item()
        item = Barang.objects.get()
        with translation.override('id'):
            response = self.client.get(reverse('barang:detail', args=[item.pk]))
        self.assertContains(response, 'query=-6.361500,106.828600')

    def test_owner_can_view_exact_pickup_address(self):
        self.post_item()
        item = Barang.objects.get()
        response = self.client.get(reverse('barang:detail', args=[item.pk]))
        self.assertContains(response, item.lokasi.full_address)
        self.assertEqual(response.context['pickup_detail_data']['latitude'], -6.3615)
