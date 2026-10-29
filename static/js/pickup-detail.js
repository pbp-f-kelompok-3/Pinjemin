(() => {
  'use strict';
  const container = document.querySelector('[data-pickup-detail-map]');
  if (!container) return;
  const status = document.querySelector('[data-pickup-detail-status]');
  if (!window.L) {
    status.textContent = 'Peta belum dapat dimuat. Gunakan tautan Google Maps untuk melihat titik penjemputan.';
    return;
  }
  const data = JSON.parse(document.getElementById('pickup-detail-data').textContent);
  const point = [data.latitude, data.longitude];
  const map = L.map(container, { scrollWheelZoom: false }).setView(point, 16);
  L.tileLayer(data.tileUrl, {
    maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).on('tileerror', () => {
    status.textContent = 'Gambar peta belum dapat dimuat. Titik penjemputan tetap bisa dibuka melalui tautan Google Maps.';
  }).addTo(map);
  const popup = document.createElement('span');
  popup.textContent = 'Titik penjemputan: ' + data.label;
  L.marker(point, {
    title: 'Titik penjemputan',
    icon: L.divIcon({ className: 'pickup-marker', html: '<span class="pickup-marker-shape"></span>',
      iconSize: [40, 44], iconAnchor: [20, 40] }),
  }).addTo(map).bindPopup(popup);
})();
