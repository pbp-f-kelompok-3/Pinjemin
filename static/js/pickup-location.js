(() => {
  'use strict';
  const root = document.querySelector('[data-pickup-picker]');
  if (!root) return;
  const find = selector => root.querySelector(selector);
  let records = JSON.parse(document.getElementById('pickup-locations-data').textContent);
  const config = JSON.parse(document.getElementById('pickup-map-config').textContent);
  const currentData = document.getElementById('pickup-current-data');
  const currentRecord = currentData ? JSON.parse(currentData.textContent) : null;
  const apiUrl = root.dataset.api;
  const manageOnly = root.dataset.manageOnly === 'true';
  const itemForm = manageOnly ? null : root.closest('form');
  const hiddenId = find('[name=pickup_location]');
  const hiddenLat = find('[name=pickup_latitude]');
  const hiddenLng = find('[name=pickup_longitude]');
  const hiddenMode = find('[name=pickup_mode]');
  const history = find('[data-history-select]');
  const status = find('[data-pickup-status]');
  const dialog = find('[data-history-dialog]');
  const draftLabel = find('[data-draft-label]');
  const draftAddress = find('[data-draft-address]');
  const manualLat = find('[data-manual-lat]');
  const manualLng = find('[data-manual-lng]');
  const googleMapsLink = find('[data-google-maps-link]');
  const saveButton = find('[data-save-location]');
  let mode = 'saved';
  let editingId = null;
  let draft = { label: '', address: '', latitude: null, longitude: null };
  let selection = null;
  let map = null;
  let marker = null;

  const number = value => value == null || String(value).trim() === '' ? null : Number(value);
  const validPoint = (lat, lng) => Number.isFinite(lat) && Number.isFinite(lng)
    && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
  const current = () => mode === 'new' ? draft : selection;
  const message = (text, error = false) => {
    status.textContent = text;
    status.classList.toggle('is-error', error);
  };
  const element = (tag, text, className = '') => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };

  const syncItem = () => {
    if (!itemForm) return;
    hiddenMode.value = mode;
    hiddenId.value = mode === 'saved' && selection ? selection.id : '';
    hiddenLat.value = mode !== 'new' && selection ? selection.latitude ?? '' : '';
    hiddenLng.value = mode !== 'new' && selection ? selection.longitude ?? '' : '';
  };

  const paintPoint = (pan = false) => {
    const point = current();
    const valid = point && validPoint(point.latitude, point.longitude);
    manualLat.value = valid ? point.latitude.toFixed(6) : '';
    manualLng.value = valid ? point.longitude.toFixed(6) : '';
    if (googleMapsLink) {
      googleMapsLink.hidden = !valid;
      if (valid) {
        const coordinates = point.latitude.toFixed(6) + ',' + point.longitude.toFixed(6);
        googleMapsLink.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(coordinates);
      } else googleMapsLink.removeAttribute('href');
    }
    if (map) {
      if (valid) {
        if (!marker) {
          marker = L.marker([point.latitude, point.longitude], {
            draggable: true, autoPan: true, title: 'Geser titik penjemputan',
            icon: L.divIcon({ className: 'pickup-marker', html: '<span class="pickup-marker-shape"></span>',
                              iconSize: [40, 44], iconAnchor: [20, 40] }),
          }).addTo(map);
          marker.on('dragend', () => {
            const position = marker.getLatLng();
            setPoint(position.lat, position.lng);
          });
        } else marker.setLatLng([point.latitude, point.longitude]);
        if (pan) map.setView([point.latitude, point.longitude], Math.max(map.getZoom(), 15));
      } else if (marker) {
        map.removeLayer(marker);
        marker = null;
      }
    }
    if (selection) {
      find('[data-selected-coordinates]').textContent = validPoint(selection.latitude, selection.longitude)
        ? `${selection.latitude.toFixed(6)}, ${selection.longitude.toFixed(6)}`
        : 'Titik peta belum ditambahkan. Klik peta untuk melengkapinya.';
    }
    syncItem();
  };

  const renderSelection = () => {
    history.value = selection ? String(selection.id) : '';
    find('[data-selected-card]').hidden = !selection;
    if (selection) {
      find('[data-selected-label]').textContent = selection.label;
      find('[data-selected-address]').textContent = selection.address;
    }
    find('[data-location-select-label]').textContent = mode === 'current'
      ? 'Lokasi penjemputan pada barang' : 'Riwayat lokasi akun';
    find('[data-selected-tag]').textContent = mode === 'current' ? 'Tercatat pada barang ini' : 'Dari riwayat akun';
    const others = records.filter(record => !selection || record.id !== selection.id);
    const list = find('[data-other-list]');
    list.replaceChildren();
    others.slice(0, 3).forEach(record => {
      const button = element('button');
      const icon = find('[data-pickup-pin-template]');
      if (icon) button.append(icon.content.cloneNode(true));
      button.append(document.createTextNode(record.label));
      button.type = 'button';
      button.addEventListener('click', () => chooseLocation(record.id));
      list.append(button);
    });
    find('[data-other-locations]').hidden = !selection || !others.length;
    paintPoint();
  };

  const renderHistory = () => {
    history.replaceChildren(new Option('Pilih lokasi tersimpan', ''));
    if (currentRecord) history.add(new Option('Lokasi saat ini: ' + currentRecord.label, 'current'));
    records.forEach(record => history.add(new Option(record.label, record.id)));
    history.disabled = !records.length && !currentRecord;
    find('[data-history-count]').textContent = `(${records.length})`;
    find('[data-history-empty]').hidden = !!records.length;
    renderSelection();
  };

  function chooseLocation(id, point = null) {
    const record = id === 'current' ? currentRecord : records.find(value => value.id === Number(id));
    selection = record === currentRecord ? currentRecord : record ? { ...record } : null;
    if (selection && point && validPoint(point.latitude, point.longitude)) {
      selection.latitude = point.latitude;
      selection.longitude = point.longitude;
    }
    setMode(selection?.id === 'current' ? 'current' : 'saved');
    renderSelection();
    paintPoint(true);
  }

  const captureDraft = () => {
    draft.label = draftLabel.value;
    draft.address = draftAddress.value;
  };

  function setMode(next, capture = true) {
    if (mode === 'new' && capture) captureDraft();
    mode = next;
    root.querySelectorAll('[data-pickup-mode]').forEach(button => {
      const active = button.dataset.pickupMode === mode;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    find('[data-history-pane]').hidden = mode === 'new';
    find('[data-new-pane]').hidden = mode !== 'new';
    draftLabel.value = draft.label;
    draftAddress.value = draft.address;
    find('[data-editor-title]').textContent = editingId ? 'Edit lokasi tersimpan' : 'Tambahkan lokasi baru';
    saveButton.textContent = editingId ? 'Simpan perubahan lokasi' : 'Simpan lokasi ke riwayat';
    paintPoint();
    if (map) requestAnimationFrame(() => map.invalidateSize());
  }

  function setPoint(latitude, longitude, pan = false) {
    const lng = ((longitude + 180) % 360 + 360) % 360 - 180;
    if (!validPoint(latitude, lng)) {
      message('Masukkan lintang antara -90 dan 90, serta bujur antara -180 dan 180.', true);
      return;
    }
    if (mode === 'saved' && !selection) setMode('new');
    if (mode === 'saved' && manageOnly) {
      draft = { ...selection };
      editingId = selection.id;
      setMode('new', false);
    }
    const point = current();
    point.latitude = Number(latitude.toFixed(6));
    point.longitude = Number(lng.toFixed(6));
    paintPoint(pan);
    message(mode === 'new' ? 'Titik dipilih. Lengkapi label dan alamat, lalu simpan lokasi.'
      : 'Titik penjemputan barang disesuaikan. Riwayat lokasi akun tetap tersimpan.');
  }

  async function api(url, method = 'GET', data = null) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {
        method, credentials: 'same-origin', signal: controller.signal,
        headers: { 'Content-Type': 'application/json',
          'X-CSRFToken': find('[name=csrfmiddlewaretoken]').value },
        ...(data ? { body: JSON.stringify(data) } : {}),
      });
      if (!response.headers.get('Content-Type')?.includes('application/json')) {
        throw new Error('Sesi halaman perlu diperbarui. Muat ulang setelah menyimpan isianmu.');
      }
      const payload = await response.json();
      if (!response.ok) {
        const details = payload.errors ? Object.values(payload.errors).flat().map(error => error.message).join(' ') : '';
        throw new Error(details || payload.error || 'Lokasi belum dapat disimpan. Coba lagi.');
      }
      return payload;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Layanan lokasi terlalu lama merespons. Coba lagi.');
      if (error instanceof TypeError) throw new Error('Koneksi terputus. Periksa jaringan dan coba lagi.');
      throw error;
    } finally { clearTimeout(timer); }
  }

  async function saveDraft() {
    if (saveButton.disabled) return;
    captureDraft();
    if (!draft.label.trim() || !draft.address.trim() || !validPoint(draft.latitude, draft.longitude)) {
      message('Isi label dan alamat, lalu pilih titik pada peta sebelum menyimpan lokasi.', true);
      return;
    }
    saveButton.disabled = true;
    const previousText = saveButton.textContent;
    saveButton.textContent = 'Menyimpan lokasi…';
    message('');
    try {
      const payload = await api(editingId ? `${apiUrl}${editingId}/` : apiUrl,
                                editingId ? 'PATCH' : 'POST', draft);
      const saved = payload.location;
      records = [saved, ...records.filter(record => record.id !== saved.id)];
      editingId = null;
      draft = { label: '', address: '', latitude: null, longitude: null };
      setMode('saved', false);
      renderHistory();
      chooseLocation(saved.id);
      message('Lokasi tersimpan di riwayat akun dan siap dipilih untuk barang ini.');
      renderManagement();
    } catch (error) { message(error.message, true); }
    finally {
      saveButton.disabled = false;
      saveButton.textContent = editingId ? previousText : 'Simpan lokasi ke riwayat';
    }
  }

  function renderManagement() {
    const list = find('[data-management-list]');
    list.replaceChildren();
    if (!records.length) list.append(element('p', 'Belum ada lokasi tersimpan.', 'pickup-help'));
    records.forEach(record => {
      const row = element('div', null, 'pickup-management-row');
      const detail = element('div');
      detail.append(element('strong', record.label), element('p', record.address));
      const actions = element('div', null, 'pickup-management-actions');
      const edit = element('button', 'Edit');
      edit.type = 'button';
      edit.dataset.editLocation = record.id;
      edit.addEventListener('click', () => {
        captureDraft();
        draft = { ...record };
        editingId = record.id;
        dialog.close();
        setMode('new', false);
        paintPoint(true);
        draftLabel.focus();
      });
      const remove = element('button', 'Hapus');
      remove.type = 'button';
      remove.dataset.deleteLocation = record.id;
      remove.addEventListener('click', async () => {
        if (!window.confirm(`Hapus ${record.label} dari riwayat? Lokasi pada barang yang sudah didaftarkan tetap tersimpan.`)) return;
        remove.disabled = true;
        try {
          await api(`${apiUrl}${record.id}/`, 'DELETE');
          records = records.filter(location => location.id !== record.id);
          if (selection?.id === record.id) selection = null;
          if (editingId === record.id) {
            editingId = null;
            draft = { label: '', address: '', latitude: null, longitude: null };
            setMode('saved', false);
          }
          renderHistory();
          renderManagement();
          find('[data-management-status]').textContent = 'Lokasi dihapus dari riwayat. Data barang tetap tersedia.';
        } catch (error) {
          find('[data-management-status]').textContent = error.message;
          remove.disabled = false;
        }
      });
      actions.append(edit, remove);
      row.append(detail, actions);
      list.append(row);
    });
  }

  const startNewLocation = () => {
    if (editingId !== null) {
      editingId = null;
      draft = { label: '', address: '', latitude: null, longitude: null };
      setMode('new', false);
    } else setMode('new');
  };
  root.querySelectorAll('[data-pickup-mode]').forEach(button => {
    button.addEventListener('click', () => {
      if (button.dataset.pickupMode === 'new') startNewLocation();
      else if (button.dataset.pickupMode === 'current') chooseLocation('current');
      else if (selection?.id === 'current' || (!selection && currentRecord)) chooseLocation(records[0]?.id);
      else setMode('saved');
    });
  });
  history.addEventListener('change', () => chooseLocation(history.value));
  saveButton.addEventListener('click', saveDraft);
  root.addEventListener('keydown', event => {
    if (event.key === 'Enter' && [draftLabel, draftAddress].includes(event.target) && event.target.tagName !== 'TEXTAREA') {
      event.preventDefault();
      saveDraft();
    }
  });
  [manualLat, manualLng].forEach(input => input.addEventListener('change', () => {
    const lat = number(manualLat.value), lng = number(manualLng.value);
    if (validPoint(lat, lng)) setPoint(lat, lng, true);
    else message('Isi kedua koordinat dengan angka yang valid.', true);
  }));
  find('[data-manage-history]').addEventListener('click', () => {
    renderManagement();
    find('[data-management-status]').textContent = '';
    dialog.showModal();
  });
  find('[data-close-history]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  find('[data-add-from-history]').addEventListener('click', () => {
    dialog.close();
    startNewLocation();
    draftLabel.focus();
  });
  find('[data-current-position]').addEventListener('click', async event => {
    const button = event.currentTarget;
    if (!window.isSecureContext || !navigator.geolocation) {
      message('Deteksi lokasi memerlukan HTTPS atau localhost dan browser yang mendukung lokasi.', true);
      return;
    }
    button.disabled = true;
    message('Menunggu izin dan posisi perangkat…');
    try {
      const position = await new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }));
      setPoint(position.coords.latitude, position.coords.longitude, true);
    } catch (error) {
      message(error.code === 1 ? 'Izin lokasi ditolak. Izinkan lokasi melalui pengaturan situs, lalu coba lagi.'
        : error.code === 3 ? 'Deteksi lokasi terlalu lama. Coba lagi atau pilih titik pada peta.'
          : 'Lokasi perangkat belum tersedia. Pilih titik pada peta atau isi koordinat.', true);
    } finally { button.disabled = false; }
  });
  if (itemForm) itemForm.addEventListener('submit', event => {
    syncItem();
    const keepLegacy = mode === 'current' && selection?.id === 'current'
      && selection.latitude == null && selection.longitude == null
      && manualLat.value.trim() === '' && manualLng.value.trim() === '';
    const validSelection = ['saved', 'current'].includes(mode) && selection
      && validPoint(selection.latitude, selection.longitude);
    if (!keepLegacy && (!validSelection || !validPoint(number(manualLat.value), number(manualLng.value)))) {
      event.preventDefault();
      message(mode === 'new' ? 'Simpan lokasi baru ke riwayat terlebih dahulu, atau pilih Lokasi saat ini.'
        : 'Pilih lokasi dan titik penjemputan yang valid sebelum menyimpan barang.', true);
      root.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  });

  if (window.L) {
    map = L.map(find('[data-pickup-map]'), { scrollWheelZoom: false, zoomControl: false,
      worldCopyJump: true }).setView(config.center, config.zoom);
    L.control.zoom({ position: 'topright' }).addTo(map);
    L.tileLayer(config.tileUrl, { maxZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' })
      .on('tileerror', () => message('Gambar peta belum dapat dimuat. Coba lagi, atau atur koordinat secara manual.', true))
      .addTo(map);
    map.on('click', event => setPoint(event.latlng.lat, event.latlng.lng));
  } else {
    find('[data-pickup-map]').textContent = 'Peta belum dapat dimuat. Kamu tetap bisa memilih titik dengan koordinat manual.';
    find('.pickup-manual').open = true;
  }

  const initialId = hiddenId?.value;
  const initialMode = hiddenMode?.value || (currentRecord ? 'current' : 'saved');
  const initialPoint = { latitude: number(hiddenLat?.value), longitude: number(hiddenLng?.value) };
  const initial = initialMode === 'current' && currentRecord ? currentRecord
    : initialId ? records.find(record => record.id === Number(initialId)) : currentRecord ? null : records[0];
  if (initial) selection = initial === currentRecord ? currentRecord : { ...initial };
  mode = initialMode === 'new' ? 'new' : selection?.id === 'current' ? 'current' : 'saved';
  if (selection && validPoint(initialPoint.latitude, initialPoint.longitude)) Object.assign(selection, initialPoint);
  setMode(mode, false);
  renderHistory();
  paintPoint(true);
})();
