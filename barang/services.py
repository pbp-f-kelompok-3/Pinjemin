from django.db import transaction
from django.db.models import Q

from .models import Lokasi


def visible_item_locations(user=None):
    legacy = Q(owner__isnull=True, is_pickup_snapshot=False)
    if user is not None and user.is_authenticated:
        return Lokasi.objects.filter(legacy | Q(owner=user))
    return Lokasi.objects.filter(legacy)


@transaction.atomic
def save_item_with_pickup(form, owner):
    item = form.save(commit=False)
    item.pemilik = owner
    source = form.cleaned_data.get('pickup_location')
    snapshot = None
    if source is not None:
        snapshot = (source.label, source.address)
    elif form.cleaned_data.get('pickup_mode') == 'current' and form.current_pickup is not None:
        current = form.current_pickup
        item.lokasi = current
        if (form.cleaned_data['pickup_latitude'], form.cleaned_data['pickup_longitude']) != (
                current.latitude, current.longitude):
            snapshot = (current.nama_area, current.full_address or current.patokan)
    if snapshot is not None:
        # Preserve old item locations and account history when the pickup point changes.
        label, address = snapshot
        item.lokasi = Lokasi.objects.create(
            owner=owner, nama_area=label, short_label=label[:50],
            patokan=address, full_address=address,
            kecamatan_kota='', kode_pos='',
            latitude=form.cleaned_data['pickup_latitude'],
            longitude=form.cleaned_data['pickup_longitude'], is_pickup_snapshot=True,
        )
    item.save()
    form.save_m2m()
    return item
