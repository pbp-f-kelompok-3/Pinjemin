(() => {
  const panel = document.querySelector('[data-payment-deadline]');
  if (!panel) return;
  const deadline = Date.parse(panel.dataset.paymentDeadline);
  const initialServer = Date.parse(panel.dataset.serverNow);
  const started = performance.now();
  const tick = () => {
    const seconds = Math.max(0, Math.ceil((deadline - initialServer - (performance.now() - started)) / 1000));
    const minutes = Math.floor(seconds / 60);
    panel.querySelector('[data-countdown]').textContent = `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
    if (!seconds) {
      panel.querySelector('[data-expired]').hidden = false;
      document.querySelectorAll('[data-pay]').forEach(button => { button.disabled = true; });
      return;
    }
    window.setTimeout(tick, 1000);
  };
  tick();
})();
