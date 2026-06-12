try {
  var mode = localStorage.getItem('atcf-color-mode') === 'dark' ? 'dark' : 'light';
  var html = document.documentElement;
  html.setAttribute('data-theme', mode);
  html.style.colorScheme = mode;
  if (mode === 'dark') {
    html.style.backgroundColor = '#1c1916';
    html.style.color = '#e8e2d9';
  } else {
    html.style.backgroundColor = '#fdfcf8';
    html.style.color = '#1a1a18';
  }
} catch (e) {}
