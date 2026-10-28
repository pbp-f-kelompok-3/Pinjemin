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

  const links = Array.from(header.querySelectorAll('.site-subnav a'));
  const currentPageLink = links.find(link => link.getAttribute('aria-current') === 'page');

  // Sections share a page, so their current marker follows the URL fragment.
  const updateCurrentLink = () => {
    const current = new URL(window.location.href);
    const sectionLink = links.find(link => {
      const target = new URL(link.href, current);
      return target.origin === current.origin && target.pathname === current.pathname
        && target.hash && target.hash === current.hash;
    });
    const activeLink = sectionLink || currentPageLink;

    links.forEach(link => {
      if (link === activeLink) {
        link.setAttribute('aria-current', sectionLink ? 'location' : 'page');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  };

  updateCurrentLink();
  window.addEventListener('hashchange', updateCurrentLink);
  window.addEventListener('popstate', updateCurrentLink);
})();
