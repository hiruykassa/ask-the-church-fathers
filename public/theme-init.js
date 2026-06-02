try {
  var mode = localStorage.getItem('atcf-color-mode') === 'dark' ? 'dark' : 'light';
  var html = document.documentElement;
  html.setAttribute('data-theme', mode);
  html.style.colorScheme = mode;
  if (mode === 'dark') {
    html.style.backgroundColor = '#000000';
    html.style.color = '#fafafa';
  } else {
    html.style.backgroundColor = '#f9f5ee';
    html.style.color = '#211a12';
  }
} catch (e) {}
