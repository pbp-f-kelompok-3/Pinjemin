(() => {
  'use strict';

  const widget = document.querySelector('[data-nearby-widget]');
  if (!widget) return;

  const mapNode = widget.querySelector('[data-nearby-map]');
  const overlay = widget.querySelector('[data-nearby-overlay]');
  const detectButton = widget.querySelector('[data-nearby-detect]');
  const overlayButton = widget.querySelector('[data-nearby-overlay-detect]');
  const locationText = widget.querySelector('[data-nearby-location-text]');
  const resultsNode = widget.querySelector('[data-nearby-results]');
  const message = widget.querySelector('[data-nearby-message]');
  const radiusButtons = [...widget.querySelectorAll('[data-nearby-radius]')];
  const fallbackCenter = [-6.3621, 106.8279];
  let radiusKm = 1;
  let userPoint = null;
  let itemLayer = null;
  let rangeCircle = null;
  let userMarker = null;

  if (!window.L) {
    message.textContent = 'Komponen peta belum dapat dimuat. Coba muat ulang halaman.';
    return;
  }

  const map = L.map(mapNode, { scrollWheelZoom: false }).setView(fallbackCenter, 14);
  L.tileLayer(widget.dataset.tileUrl, {
    maxZoom: 19,
    referrerPolicy: 'strict-origin-when-cross-origin',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).on('tileerror', () => {
    setMessage('Peta belum dapat dimuat. Periksa koneksi internet, lalu coba lagi.', true);
  }).addTo(map);
  itemLayer = L.layerGroup().addTo(map);

  function setMessage(text, isError = false) {
    message.textContent = text;
    message.dataset.error = String(isError);
  }

  function formatDistance(distance) {
    if (distance < 0.1) return 'Kurang dari 100 m';
    return `${distance.toLocaleString('id-ID', { maximumFractionDigits: 1 })} km`;
  }

  function makeItemCard(item) {
    const link = document.createElement('a');
    link.className = 'nearby-item';
    link.href = item.url;
    link.setAttribute('aria-label', `${item.name}, ${item.offer}, ${formatDistance(item.distance_km)}`);

    if (item.image) {
      const image = document.createElement('img');
      image.src = item.image;
      image.alt = '';
      image.loading = 'lazy';
      link.append(image);
    } else {
      const placeholder = document.createElement('span');
      placeholder.className = 'nearby-item-placeholder';
      placeholder.textContent = '⌂';
      link.append(placeholder);
    }

    const copy = document.createElement('span');
    copy.className = 'nearby-item-copy';
    const name = document.createElement('span');
    name.className = 'nearby-item-name';
    name.textContent = item.name;
    const price = document.createElement('span');
    price.className = 'nearby-item-price';
    price.textContent = item.offer === 'Gratis' ? 'Pinjam gratis' : `Rp${item.price} / hari`;
    const meta = document.createElement('span');
    meta.className = 'nearby-item-meta';
    const area = document.createElement('span');
    area.textContent = item.area;
    const distance = document.createElement('span');
    distance.textContent = formatDistance(item.distance_km);
    meta.append(area, distance);
    copy.append(name, price, meta);
    link.append(copy);
    return link;
  }

  function makeMarker(item, index) {
    const point = [item.latitude, item.longitude];
    const marker = L.marker(point, {
      title: item.name,
      icon: L.divIcon({
        className: '',
        html: `<span class="nearby-item-marker"><span>${index + 1}</span></span>`,
        iconSize: [32, 32],
        iconAnchor: [16, 29],
      }),
    }).addTo(itemLayer);
    const popup = document.createElement('div');
    popup.className = 'nearby-popup';
    const title = document.createElement('strong');
    title.textContent = item.name;
    const detail = document.createElement('div');
    detail.textContent = `${item.offer === 'Gratis' ? 'Gratis' : `Rp${item.price} / hari`} · ${formatDistance(item.distance_km)}`;
    const link = document.createElement('a');
    link.href = item.url;
    link.textContent = 'Lihat barang';
    popup.append(title, detail, link);
    marker.bindPopup(popup);
  }

  async function loadNearby() {
    if (!userPoint) return;
    setMessage('Memuat barang di sekitarmu…');
    const query = new URLSearchParams({
      latitude: String(userPoint.latitude),
      longitude: String(userPoint.longitude),
      radius: String(radiusKm),
    });
    try {
      const response = await fetch(`${widget.dataset.endpoint}?${query}`, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Barang terdekat belum dapat dimuat.');

      itemLayer.clearLayers();
      resultsNode.replaceChildren();
      if (rangeCircle) rangeCircle.remove();
      if (userMarker) userMarker.remove();
      rangeCircle = L.circle([userPoint.latitude, userPoint.longitude], {
        radius: radiusKm * 1000,
        color: '#e4bd00',
        weight: 1.5,
        dashArray: '5 6',
        fillColor: '#ffde01',
        fillOpacity: 0.08,
      }).addTo(map);
      userMarker = L.marker([userPoint.latitude, userPoint.longitude], {
        title: 'Posisimu',
        icon: L.divIcon({ className: '', html: '<span class="nearby-user-marker"></span>',
          iconSize: [20, 20], iconAnchor: [10, 10] }),
      }).addTo(map);
      userMarker.bindTooltip('Kamu di sini');

      const items = data.items || [];
      if (!items.length) {
        const empty = document.createElement('div');
        empty.className = 'nearby-empty';
        const title = document.createElement('h3');
        title.textContent = `Belum ada barang dalam radius ${radiusKm} km`;
        const copy = document.createElement('p');
        copy.textContent = 'Perluas radius atau lihat katalog barang yang tersedia.';
        const link = document.createElement('a');
        link.href = '#barang';
        link.textContent = 'Lihat katalog';
        empty.append(title, copy, link);
        resultsNode.append(empty);
        setMessage(`Belum ada barang dalam radius ${radiusKm} km.`);
      } else {
        const heading = document.createElement('h3');
        heading.className = 'nearby-list-heading';
        heading.textContent = `${items.length} barang dalam radius ${radiusKm} km`;
        resultsNode.append(heading);
        items.forEach((item, index) => {
          resultsNode.append(makeItemCard(item));
          makeMarker(item, index);
        });
        setMessage(`${items.length} barang tersedia di sekitarmu.`);
      }

      const bounds = L.latLngBounds([[userPoint.latitude, userPoint.longitude]]);
      items.slice(0, 50).forEach((item) => bounds.extend([item.latitude, item.longitude]));
      if (items.length) map.fitBounds(bounds.pad(0.18), { maxZoom: 16 });
      else map.setView([userPoint.latitude, userPoint.longitude], radiusKm === 1 ? 15 : 14);
      map.invalidateSize();
    } catch (error) {
      setMessage(error instanceof TypeError
        ? 'Tidak dapat memuat barang terdekat. Periksa koneksi internet, lalu coba lagi.'
        : error.message, true);
    }
  }

  function requestLocation() {
    if (!window.isSecureContext) {
      setMessage('Akses lokasi hanya tersedia melalui koneksi aman. Buka situs dengan HTTPS, lalu coba lagi.', true);
      return;
    }
    if (!navigator.geolocation) {
      setMessage('Browser ini tidak mendukung akses lokasi.', true);
      return;
    }
    detectButton.disabled = true;
    overlayButton.disabled = true;
    detectButton.textContent = 'Mencari lokasi…';
    setMessage('Menunggu izin akses lokasi…');
    navigator.geolocation.getCurrentPosition((position) => {
      userPoint = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };
      const accuracy = Math.round(position.coords.accuracy);
      locationText.replaceChildren();
      locationText.append(document.createTextNode('Lokasi aktif'));
      const note = document.createElement('small');
      note.textContent = `Perkiraan akurasi lokasi: ±${accuracy} m.`;
      locationText.append(note);
      overlay.hidden = true;
      detectButton.textContent = 'Perbarui lokasi';
      detectButton.disabled = false;
      overlayButton.disabled = false;
      map.setView([userPoint.latitude, userPoint.longitude], 15);
      loadNearby();
    }, (error) => {
      const messages = {
        1: 'Izin lokasi ditolak. Izinkan akses lokasi lewat pengaturan browser.',
        2: 'Lokasi belum bisa ditemukan. Periksa pengaturan lokasi perangkat.',
        3: 'Pencarian lokasi memakan waktu terlalu lama. Coba lagi.',
      };
      setMessage(messages[error.code] || 'Lokasi belum dapat dideteksi. Coba lagi.', true);
      detectButton.textContent = userPoint ? 'Perbarui lokasi' : 'Gunakan lokasi saya';
      detectButton.disabled = false;
      overlayButton.disabled = false;
    }, { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
  }

  detectButton.addEventListener('click', requestLocation);
  overlayButton.addEventListener('click', requestLocation);
  radiusButtons.forEach((button) => button.addEventListener('click', () => {
    radiusKm = Number(button.dataset.nearbyRadius);
    radiusButtons.forEach((entry) => entry.setAttribute('aria-pressed', String(entry === button)));
    if (userPoint) loadNearby();
  }));
})();
