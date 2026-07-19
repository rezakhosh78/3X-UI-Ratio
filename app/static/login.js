(() => {
  const words = {
    en: {
      tagline: '3X-UI Independent Quota Management',
      username: 'Username', password: 'Password', sign_in: 'Sign in', version: 'Version',
      wrong: 'Incorrect username or password.', title: 'Sign in | 3X-UI Ratio',
      light: 'Light', dark: 'Dark', themeAria: 'Change color theme'
    },
    fa: {
      tagline: 'مدیریت مستقل حجم 3X-UI',
      username: 'نام کاربری', password: 'رمز عبور', sign_in: 'ورود', version: 'نسخه',
      wrong: 'نام کاربری یا رمز عبور نادرست است.', title: 'ورود | 3X-UI Ratio',
      light: 'روشن', dark: 'تیره', themeAria: 'تغییر پوسته رنگی'
    }
  };

  let lang = 'en';
  let theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';

  function updateThemeButton() {
    const button = document.querySelector('#login-theme-toggle');
    if (!button) return;
    const targetLight = theme === 'dark';
    button.textContent = `${targetLight ? '☀' : '☾'} ${targetLight ? words[lang].light : words[lang].dark}`;
    button.setAttribute('aria-label', words[lang].themeAria);
  }

  function applyTheme(value, persist = true) {
    theme = value === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    if (persist) localStorage.setItem('ratio-theme', theme);
    updateThemeButton();
  }

  function applyLanguage(value) {
    lang = value === 'fa' ? 'fa' : 'en';
    localStorage.setItem('ratio-language', lang);
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr';
    document.title = words[lang].title;
    document.querySelectorAll('[data-login-i18n]').forEach((element) => {
      element.textContent = words[lang][element.dataset.loginI18n];
    });
    const button = document.querySelector('#login-language-toggle');
    if (button) button.textContent = lang === 'fa' ? 'English' : 'فارسی';
    const error = document.querySelector('[data-login-error]');
    if (error && [words.en.wrong, words.fa.wrong].includes(error.textContent.trim())) {
      error.textContent = words[lang].wrong;
    }
    updateThemeButton();
  }

  document.addEventListener('DOMContentLoaded', () => {
    const savedLanguage = localStorage.getItem('ratio-language');
    lang = savedLanguage === 'fa' || savedLanguage === 'en'
      ? savedLanguage
      : (navigator.language?.toLowerCase().startsWith('fa') ? 'fa' : 'en');
    const savedTheme = localStorage.getItem('ratio-theme');
    theme = savedTheme === 'light' || savedTheme === 'dark'
      ? savedTheme
      : (document.documentElement.dataset.theme || 'dark');
    applyTheme(theme, false);
    applyLanguage(lang);
    document.querySelector('#login-language-toggle').onclick = () => applyLanguage(lang === 'fa' ? 'en' : 'fa');
    document.querySelector('#login-theme-toggle').onclick = () => applyTheme(theme === 'dark' ? 'light' : 'dark');
  });
})();
