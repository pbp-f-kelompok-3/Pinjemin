(() => {
  'use strict';
  const form = document.querySelector('[data-item-create]');
  if (!form) return;
  const find = selector => form.querySelector(selector);
  const fileInput = find('#id_foto_utama');
  const preview = find('[data-photo-preview]');
  const choose = find('[data-choose-photo]');
  const error = find('[data-photo-error]');
  let previewUrl;
  fileInput.setAttribute('aria-describedby', 'photo-help');
  choose.addEventListener('click', () => fileInput.click());
  const showPhoto = () => {
    const file = fileInput.files[0];
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    preview.removeAttribute('src');
    preview.hidden = true;
    find('[data-photo-placeholder]').hidden = false;
    error.textContent = '';
    choose.textContent = 'Pilih foto';
    find('[data-photo-name]').textContent = 'Tambahkan foto barangmu';
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      error.textContent = 'Gunakan foto JPG, PNG, atau WebP dengan ukuran maksimal 5 MB.';
      fileInput.value = '';
      return;
    }
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    find('[data-photo-placeholder]').hidden = true;
    find('[data-photo-name]').textContent = file.name;
    choose.textContent = 'Ganti foto';
  };
  fileInput.addEventListener('change', showPhoto);
  preview.addEventListener('error', () => {
    if (!preview.getAttribute('src')) return;
    preview.hidden = true;
    find('[data-photo-placeholder]').hidden = false;
    fileInput.value = '';
    choose.textContent = 'Pilih foto';
    find('[data-photo-name]').textContent = 'Tambahkan foto barangmu';
    error.textContent = 'Foto tidak dapat dibaca. Pilih file gambar lain.';
  });
  const zone = find('[data-upload-zone]');
  zone.addEventListener('dragover', event => event.preventDefault());
  zone.addEventListener('drop', event => {
    event.preventDefault();
    if (!event.dataTransfer.files.length) return;
    const transfer = new DataTransfer();
    transfer.items.add(event.dataTransfer.files[0]);
    fileInput.files = transfer.files;
    showPhoto();
  });
  fileInput.addEventListener('invalid', () => {
    error.textContent = 'Tambahkan foto barang sebelum mendaftar.';
    choose.focus();
  });
  window.addEventListener('pagehide', () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });

  const offer = find('#id_jenis_penawaran');
  const price = find('#id_tarif_per_hari');
  let rentalPrice = price.value;

  let priceError = find('[data-price-error]');
  if (!priceError) {
    priceError = document.createElement('p');
    priceError.className = 'pickup-error';
    priceError.setAttribute('data-price-error', '');
    priceError.style.color = '#DC2626';
    priceError.style.fontSize = '12.5px';
    priceError.style.fontWeight = '600';
    priceError.style.marginTop = '6px';
    const priceGroup = find('[data-price-group]');
    if (priceGroup) priceGroup.appendChild(priceError);
  }

  const checkPriceValidity = () => {
    if (offer.value === 'sewa') {
      const val = Number(price.value);
      if (price.value === '' || isNaN(val)) {
        priceError.textContent = '⚠️ Tarif sewa harian wajib diisi untuk barang sewa.';
        priceError.hidden = false;
        return false;
      } else if (val <= 0) {
        priceError.textContent = '⚠️ Tarif sewa harian tidak boleh Rp 0 atau bernilai minus. Harap masukkan nominal minimal Rp 1.';
        priceError.hidden = false;
        return false;
      } else {
        priceError.textContent = '';
        priceError.hidden = true;
        return true;
      }
    } else {
      priceError.textContent = '';
      priceError.hidden = true;
      return true;
    }
  };

  const updatePrice = () => {
    const free = offer.value === 'gratis';
    find('[data-price-group]').hidden = free;
    find('[data-free-note]').hidden = !free;
    price.required = !free;
    price.min = free ? '0' : '1';
    price.step = '1';
    price.value = free ? '0' : (rentalPrice && Number(rentalPrice) > 0 ? rentalPrice : '');
    checkPriceValidity();
  };

  price.addEventListener('input', () => {
    rentalPrice = price.value;
    checkPriceValidity();
  });
  offer.addEventListener('change', updatePrice);
  updatePrice();

  form.addEventListener('submit', event => {
    if (!checkPriceValidity()) {
      event.preventDefault();
      price.focus();
      price.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  });
})();