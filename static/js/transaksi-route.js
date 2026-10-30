(() => {
  'use strict';

  const mapNode = document.querySelector('[data-order-map]');
  const dataNode = document.getElementById('order-pickup-data');
  if (!mapNode || !dataNode) return;

  const data = JSON.parse(dataNode.textContent);
  const routeButton = document.querySelector('[data-order-route]');
  const status = document.querySelector('[data-order-route-status]');
  const summary = document.querySelector('[data-order-route-summary]');
  const stepsList = document.querySelector('[data-order-route-steps]');
  if (!window.L) {
    status.textContent = 'Peta tidak dapat dimuat. Kamu tetap bisa membuka rute melalui Google Maps.';
    status.dataset.error = 'true';
    return;
  }

  const destination = [Number(data.latitude), Number(data.longitude)];
  const map = L.map(mapNode, { scrollWheelZoom: false }).setView(destination, 16);
  L.tileLayer(data.tileUrl, {
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).on('tileerror', () => {
    setStatus('Peta belum dapat dimuat. Periksa koneksi internet atau buka rute di Google Maps.', true);
  }).addTo(map);

  const destinationMarker = L.marker(destination, {
    title: 'Titik penjemputan barang',
    icon: L.divIcon({ className: '', html: '<span class="tr-destination-marker"><span>⌖</span></span>',
      iconSize: [34, 34], iconAnchor: [17, 31] }),
  }).addTo(map);
  const destinationPopup = document.createElement('span');
  destinationPopup.textContent = `Titik penjemputan: ${data.label}`;
  destinationMarker.bindPopup(destinationPopup);

  let routeLayer = null;
  let originMarker = null;
  let requestController = null;

  function setStatus(text, isError = false) {
    status.textContent = text;
    status.dataset.error = String(isError);
  }

  function formatDistance(meters) {
    if (meters < 1000) return `${Math.round(meters)} m`;
    return `${(meters / 1000).toLocaleString('id-ID', { maximumFractionDigits: 1 })} km`;
  }

  function formatDuration(seconds) {
    const minutes = Math.max(1, Math.round(seconds / 60));
    if (minutes < 60) return `±${minutes} menit`;
    const hours = Math.floor(minutes / 60);
    const remaining = minutes % 60;
    return remaining ? `±${hours} jam ${remaining} menit` : `±${hours} jam`;
  }

  function instruction(step) {
    const type = step.maneuver?.type || 'continue';
    const modifier = step.maneuver?.modifier || '';
    const turns = {
      'sharp right': 'tajam ke kanan', right: 'ke kanan', 'slight right': 'sedikit ke kanan',
      straight: 'lurus', 'slight left': 'sedikit ke kiri', left: 'ke kiri',
      'sharp left': 'tajam ke kiri', uturn: 'putar balik',
    };
    const direction = turns[modifier];
    const names = {
      depart: 'Mulai perjalanan', arrive: 'Kamu tiba di tujuan',
      turn: direction ? `Belok ${direction}` : 'Ikuti arah jalan',
      'end of road': direction ? `Di ujung jalan, belok ${direction}` : 'Ikuti jalan hingga ujung',
      fork: direction ? `Ambil cabang ${direction}` : 'Pilih cabang jalan',
      merge: 'Bergabung ke jalan', 'on ramp': 'Masuk ke jalan penghubung',
      'off ramp': 'Keluar dari jalan penghubung', roundabout: 'Masuk bundaran',
      rotary: 'Masuk bundaran', 'roundabout turn': direction ? `Di bundaran, ambil arah ${direction}` : 'Lanjutkan di bundaran',
      'exit roundabout': 'Keluar dari bundaran', 'exit rotary': 'Keluar dari bundaran',
      continue: direction ? `Lanjut ${direction}` : 'Lanjutkan perjalanan',
      'new name': 'Lanjut ke jalan berikutnya', notification: 'Perhatikan perubahan jalan',
    };
    const action = names[type] || (direction ? `Lanjut ${direction}` : 'Lanjutkan perjalanan');
    const road = step.name ? ` ke ${step.name}` : '';
    return `${action}${road}`;
  }

  function renderDirections(route) {
    const leg = route.legs?.[0];
    if (!leg) throw new Error('Petunjuk rute tidak tersedia untuk perjalanan ini.');

    summary.replaceChildren();
    const distancePill = document.createElement('span');
    distancePill.className = 'tr-route-pill';
    distancePill.textContent = `Jarak jalan ${formatDistance(route.distance)}`;
    const durationPill = document.createElement('span');
    durationPill.className = 'tr-route-pill';
    durationPill.textContent = formatDuration(route.duration);
    summary.append(distancePill, durationPill);
    summary.hidden = false;

    stepsList.replaceChildren();
    (leg.steps || []).forEach((step, index) => {
      const row = document.createElement('li');
      const icon = document.createElement('span');
      icon.className = 'tr-route-step-icon';
      icon.textContent = step.maneuver?.type === 'arrive' ? '●' : String(index + 1);
      const text = document.createElement('span');
      text.append(document.createTextNode(instruction(step)));
      const distance = document.createElement('small');
      distance.className = 'tr-route-step-distance';
      distance.textContent = formatDistance(step.distance || 0);
      text.append(distance);
      row.append(icon, text);
      stepsList.append(row);
    });
    stepsList.hidden = !leg.steps?.length;
  }

  function getDevicePosition() {
    return new Promise((resolve, reject) => {
      if (!window.isSecureContext) {
        reject(new Error('Akses lokasi memerlukan HTTPS atau alamat localhost.'));
        return;
      }
      if (!navigator.geolocation) {
        reject(new Error('Browser ini belum mendukung lokasi perangkat.'));
        return;
      }
      navigator.geolocation.getCurrentPosition(resolve, (error) => {
        const errors = {
          1: 'Izin lokasi ditolak. Izinkan lokasi di browser atau gunakan Google Maps.',
          2: 'Posisi belum tersedia. Aktifkan layanan lokasi lalu coba lagi.',
          3: 'Pencarian lokasi terlalu lama. Coba lagi.',
        };
        reject(new Error(errors[error.code] || 'Lokasi belum dapat dideteksi.'));
      }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
    });
  }

  async function findRoute() {
    routeButton.disabled = true;
    routeButton.textContent = 'Mencari rute…';
    summary.hidden = true;
    stepsList.hidden = true;
    setStatus('Meminta akses lokasi perangkat…');
    if (requestController) requestController.abort();

    try {
      const position = await getDevicePosition();
      const origin = [position.coords.latitude, position.coords.longitude];
      setStatus('Menghitung rute jalan dari OpenStreetMap…');

      const endpoint = `${data.routeUrl}/driving/${origin[1]},${origin[0]};${destination[1]},${destination[0]}`;
      const url = new URL(endpoint);
      url.searchParams.set('overview', 'full');
      url.searchParams.set('geometries', 'geojson');
      url.searchParams.set('steps', 'true');
      requestController = new AbortController();
      const timeout = window.setTimeout(() => requestController.abort(), 20000);
      let response;
      let payload;
      try {
        response = await fetch(url, { signal: requestController.signal, mode: 'cors' });
        payload = await response.json();
      } finally {
        window.clearTimeout(timeout);
      }
      if (!response.ok || payload.code !== 'Ok' || !payload.routes?.length) {
        throw new Error(payload.message || 'Rute jalan tidak ditemukan. Coba buka Google Maps.');
      }

      const route = payload.routes[0];
      if (!route.geometry?.coordinates?.length) throw new Error('Garis rute tidak tersedia. Coba lagi.');
      if (routeLayer) routeLayer.remove();
      if (originMarker) originMarker.remove();
      routeLayer = L.geoJSON(route.geometry, {
        style: { color: '#2463b5', weight: 6, opacity: 0.86, lineCap: 'round', lineJoin: 'round' },
      }).addTo(map);
      originMarker = L.marker(origin, {
        title: 'Lokasi awalmu',
        icon: L.divIcon({ className: '', html: '<span class="tr-origin-marker"></span>',
          iconSize: [22, 22], iconAnchor: [11, 11] }),
      }).addTo(map);
      originMarker.bindTooltip('Lokasimu');
      map.fitBounds(routeLayer.getBounds().pad(0.15));
      renderDirections(route);
      setStatus('Rute rekomendasi siap. Perkiraan waktu dapat berubah mengikuti kondisi jalan.');
    } catch (error) {
      const message = error.name === 'AbortError'
        ? 'Layanan rute terlalu lama merespons. Coba lagi atau gunakan Google Maps.'
        : error instanceof TypeError
          ? 'Tidak dapat menghubungi layanan rute. Coba lagi atau gunakan Google Maps.'
          : error.message;
      setStatus(message, true);
    } finally {
      requestController = null;
      routeButton.disabled = false;
      routeButton.textContent = 'Rute dari lokasiku';
    }
  }

  routeButton.addEventListener('click', findRoute);
  window.requestAnimationFrame(() => map.invalidateSize());
})();
