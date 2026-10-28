(() => {
  'use strict';

  const header = document.querySelector('.site-header');
  if (!header) return;

  // Keep anchor destinations and sticky sidebars below the responsive header.
  const updateHeaderHeight = () => {
    document.documentElement.style.setProperty(
      '--site-header-height', `${header.offsetHeight}px`,
    );
  };

  updateHeaderHeight();
  if ('ResizeObserver' in window) {
    new ResizeObserver(updateHeaderHeight).observe(header);
  } else {
    window.addEventListener('resize', updateHeaderHeight);
  }
})();
