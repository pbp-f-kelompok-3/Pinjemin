(() => {
  'use strict';

  const widget = document.querySelector('[data-location-widget]');
  if (!widget) return;

  const form = widget.querySelector('[data-location-form]');
  const button = widget.querySelector('[data-location-detect]');
  const label = widget.querySelector('[data-location-label]');
  const caption = widget.querySelector('[data-location-caption]');
  const status = widget.querySelector('[data-location-status]');
  const toggle = widget.querySelector('[data-location-toggle]');
  const panel = widget.querySelector('#location-panel');
  const close = widget.querySelector('[data-location-close]');
  const selected = widget.querySelector('[data-location-selected]');
  const storageKey = 'pinjemin.location';
  let hasLocation = false;
  let retryAt = 0;

  const setOpen = (open, returnFocus = false) => {
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    if (open) button.focus();
    else if (returnFocus) toggle.focus();
  };

  toggle.addEventListener('click', () => setOpen(panel.hidden));
  close.addEventListener('click', () => setOpen(false, true));
  widget.addEventListener('focusout', (event) => {
    if (!widget.contains(event.relatedTarget)) setOpen(false);
  });

  const showStatus = (message, isError = false) => {
    status.textContent = message;
    status.classList.toggle('nav-location__status--error', isError);
  };

  // Remember only the area label in this tab; a remembered value is explicitly marked.
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey));
    if (saved && typeof saved.label === 'string' && saved.label.trim() && saved.label.length <= 120
        && Number.isFinite(saved.detectedAt) && saved.detectedAt <= Date.now()
        && Date.now() - saved.detectedAt < 15 * 60 * 1000) {
      hasLocation = true;
      label.textContent = saved.label;
      selected.textContent = saved.label;
      caption.textContent = 'Lokasi terakhir';
      button.textContent = 'Perbarui lokasi';
      showStatus(`Lokasi terakhir: ${saved.label}. Perbarui untuk mengambil posisi saat ini.`);
    }
  } catch {
    // Location detection also works when browser storage is disabled.
  }

  const getPosition = () => new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    });
  });

  const geolocationMessage = (error) => {
    switch (error.code) {
      case 1:
        return 'Izin lokasi ditolak. Izinkan lokasi melalui pengaturan situs di browser, lalu coba lagi.';
      case 2:
        return 'Posisi perangkat belum tersedia. Aktifkan layanan lokasi perangkat dan coba lagi.';
      case 3:
        return 'Deteksi lokasi terlalu lama. Pastikan layanan lokasi aktif, lalu coba lagi.';
      default:
        return 'Lokasi belum dapat dideteksi. Silakan coba lagi.';
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (button.disabled) return;
    if (!window.isSecureContext) {
      showStatus('Deteksi lokasi memerlukan HTTPS atau akses melalui localhost.', true);
      return;
    }
    if (!navigator.geolocation) {
      showStatus('Browser ini belum mendukung deteksi lokasi.', true);
      return;
    }
    if (Date.now() < retryAt) {
      const seconds = Math.ceil((retryAt - Date.now()) / 1000);
      showStatus(`Tunggu ${seconds} detik sebelum mencoba lagi.`, true);
      return;
    }

    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    button.textContent = 'Mendeteksi lokasi…';
    showStatus('Menunggu izin dan posisi dari perangkat…');
    if (hasLocation) caption.textContent = 'Lokasi terakhir';

    try {
      let position;
      try {
        position = await getPosition();
      } catch (error) {
        throw new Error(geolocationMessage(error));
      }
      showStatus('Mencari nama wilayah…');
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      let payload;
      let response;
      try {
        response = await fetch(widget.dataset.endpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value,
          },
          body: JSON.stringify({
            latitude: Number(position.coords.latitude.toFixed(3)),
            longitude: Number(position.coords.longitude.toFixed(3)),
          }),
          signal: controller.signal,
        });
        if (response.status === 429) {
          const wait = Number(response.headers.get('Retry-After'));
          retryAt = Date.now() + (Number.isFinite(wait) && wait > 0 ? wait : 2) * 1000;
        }
        if (response.status === 403) {
          throw new Error('Sesi halaman perlu diperbarui. Muat ulang halaman, lalu coba lagi.');
        }
        if (!response.headers.get('Content-Type')?.includes('application/json')) {
          throw new Error('Layanan lokasi sedang tidak tersedia. Coba lagi nanti.');
        }
        payload = await response.json();
      } finally {
        clearTimeout(timeout);
      }
      if (!response.ok) {
        throw new Error(payload.error || 'Nama wilayah belum dapat ditemukan. Coba lagi.');
      }
      if (typeof payload.label !== 'string' || !payload.label.trim() || payload.label.length > 120) {
        throw new Error('Nama wilayah belum dapat ditemukan. Coba lagi.');
      }
      label.textContent = payload.label;
      selected.textContent = payload.label;
      caption.textContent = 'Lokasi kamu';
      hasLocation = true;
      showStatus(`Lokasi diperbarui: ${payload.label}.`);
      if (!panel.hidden) setOpen(false, true);
      try {
        sessionStorage.setItem(storageKey, JSON.stringify({
          label: payload.label, detectedAt: Date.now(),
        }));
      } catch {
        // Storing the label is optional.
      }
    } catch (error) {
      const message = error.name === 'AbortError'
        ? 'Layanan lokasi terlalu lama merespons. Silakan coba lagi.'
        : error instanceof TypeError
          ? 'Tidak dapat menghubungi layanan lokasi. Periksa koneksi dan coba lagi.'
          : error.message;
      showStatus(message, true);
    } finally {
      button.disabled = false;
      form.removeAttribute('aria-busy');
      button.textContent = hasLocation ? 'Perbarui lokasi' : 'Gunakan lokasi saat ini';
    }
  });

  document.addEventListener('click', (event) => {
    if (!widget.contains(event.target)) setOpen(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) {
      setOpen(false, true);
    }
  });
})();
