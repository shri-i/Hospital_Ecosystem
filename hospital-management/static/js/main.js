// main.js - small helpers used on several pages

// Ask before any form marked with data-confirm is submitted (delete / cancel buttons)
document.addEventListener('submit', function (e) {
  const msg = e.target.getAttribute('data-confirm');
  if (msg && !confirm(msg)) {
    e.preventDefault();
  }
});

// Hide success / info flash messages after a few seconds
setTimeout(function () {
  document.querySelectorAll('.alert-success, .alert-info').forEach(function (el) {
    if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(el).close();
  });
}, 5000);
