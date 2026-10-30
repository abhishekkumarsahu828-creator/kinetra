'use strict';
(() => {
  const menuButton = document.getElementById('menu-button');
  const mainNav = document.getElementById('main-nav');
  if (menuButton && mainNav) {
    menuButton.addEventListener('click', () => {
      const expanded = menuButton.getAttribute('aria-expanded') === 'true';
      menuButton.setAttribute('aria-expanded', String(!expanded));
      menuButton.setAttribute('aria-label', expanded ? 'Open navigation' : 'Close navigation');
      mainNav.classList.toggle('is-open', !expanded);
    });
    window.addEventListener('keydown', e => {
      if (e.key === 'Escape' && mainNav.classList.contains('is-open')) {
        mainNav.classList.remove('is-open');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.focus();
      }
    });
  }
  document.querySelectorAll('[data-dismiss]').forEach(button => {
    button.addEventListener('click', () => button.closest('.toast')?.classList.add('is-hidden'));
  });
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm || 'Are you sure?')) event.preventDefault();
    });
  });
  document.querySelectorAll('form[data-submit-lock]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!form.checkValidity()) return;
      const submitter = e.submitter;
      if (form.dataset.submitted === 'true') { e.preventDefault(); return; }
      form.dataset.submitted = 'true';
      if (submitter) {
        // Never disable the clicked submit button: named action fields must be submitted.
        submitter.setAttribute('aria-disabled','true');
        submitter.style.opacity = '0.7';
      }
    });
  });
})();
