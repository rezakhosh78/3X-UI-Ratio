const state = {
  overview: null,
  users: [],
  selectedIds: new Set(),
  quotaTargets: [],
  quotaMode: 'single',
  lang: 'en',
  theme: document.documentElement.dataset.theme === 'light' ? 'light' : 'dark',
  refreshTimer: null
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const translations = {
  en: {
    nav_users: 'Users', nav_audit: 'Logs', nav_connection: 'Connection', nav_backup: 'Backup & Restore', sign_out: 'Sign out',
    title_users: 'User management', title_events: 'Logs', title_settings: '3X-UI connection', title_database: 'Backup & Restore',
    loading_status: 'Loading status…', synchronize: 'Synchronize', engine_loading: 'Ratio…', engine_on: 'Ratio ON', engine_off: 'Ratio OFF',
    engine_paused_banner: 'Ratio is paused. Synchronization, traffic reads, quota changes, enforcement, connection tests, and client status changes are disabled.',
    total_users: 'Total users', enabled_3xui: 'Enabled in 3X-UI', managed_ratio: 'Managed by Ratio', quota_exhausted: 'Quota exhausted',
    search_users: 'Search users…', user: 'User', subscription_usage: 'Subscription usage', ratio_usage: 'Ratio cycle usage', quota: 'Quota', status: 'Status', actions: 'Actions', loading: 'Loading…',
    select_all_users: 'Select all visible users', selected_none: '0 selected', selected_count: '{count} selected', apply_quota_selected: 'Apply quota to selected',
    start_selected_enforcement: 'Start Enforcement', start_selected_confirm: 'Start quota enforcement for the selected users?', start_selected_done: 'Enforcement started for {count} users. {skipped} selected users were skipped because no quota is set.',
    theme_toggle_aria: 'Change color theme', switch_to_light: 'Light', switch_to_dark: 'Dark',
    stop_all_enforcement: 'Stop All Enforcement', stop_all_enforcement_confirm: 'Stop quota enforcement for every active Ratio user? This does not disable or delete any client in 3X-UI.', stop_all_enforcement_done: 'Enforcement stopped for {count} users.',
    bulk_quota_title: 'Apply quota to selected users', selected_users: '{count} selected users', no_users_selected: 'Select at least one user first.', bulk_quota_saved: 'Quota applied to {count} users.',
    time: 'Time', level: 'Level', event_action: 'Action', message: 'Message', connection_heading: '3X-UI connection', connection_note: 'Ratio never connects directly to the 3X-UI database.',
    panel_url: 'Complete panel URL', api_token: 'API token', token_placeholder: 'Leave blank to keep the saved token', token_help: 'Paste the plaintext token shown once when it is created.',
    subscription_base: 'Subscription base URL', subscription_help: 'Enter the subscription service URL without a client subId. Ratio receives each subId from 3X-UI and appends it automatically.', subid_example: 'CLIENT_SUB_ID',
    poll_interval: 'Polling interval, seconds', request_timeout: 'Request timeout, seconds', verify_tls: 'Verify TLS certificates', auto_disable: 'Automatically disable exhausted users',
    test_connection: 'Test connection and subscription', save_settings: 'Save settings', download_backup: 'Download database backup', download_backup_desc: 'Create a consistent SQLite snapshot of users, quotas, usage counters, audit events, and encrypted connection settings.',
    backup_warning: 'Backups contain sensitive encrypted configuration. Store them securely. Restoring on another installation requires the same ENCRYPTION_KEY.', create_backup: 'Create and download backup',
    import_backup: 'Import database backup', import_backup_desc: 'Restore a Ratio backup. The current database is automatically saved as a restore point first.', backup_file: 'Backup file', type_restore: 'Type', to_confirm: 'to confirm', restore_warning: 'Restore replaces the current Ratio database. It does not modify the 3X-UI database.', restore_button: 'Import and restore database',
    set_quota: 'Set quota', new_quota: 'New quota (GB)', disable_after_quota: 'Disable the user after quota exhaustion', start_new_cycle: 'Start a new Ratio usage cycle now', cancel: 'Cancel', save_quota: 'Save quota',
    users_count: '{count} users', no_users: 'No users found.', no_subid: 'No subId', upload: 'Upload', download: 'Download', total: 'Total', unlimited_unknown: 'Unlimited / unavailable', not_set: 'Not set', no_ratio_limit: 'No Ratio limit', used_percent: '{percent}% used',
    enabled: 'Enabled', disabled: 'Disabled', enforcement_on: 'Quota enforcement on', enforcement_off: 'Quota enforcement off', set_quota_action: 'Set quota', reset_cycle: 'Reset cycle', turn_enforcement_off: 'Stop enforcement', turn_enforcement_on: 'Start enforcement', enable_user: 'Enable', disable_user: 'Disable',
    last_sync: 'Last synchronization', last_attempt: 'Last attempt', no_sync: 'No synchronization has run yet.', not_configured: 'The 3X-UI connection is not configured.', engine_disabled_caption: 'Ratio is paused. All operational processing is stopped.',
    sync_running: 'Synchronizing…', sync_complete: 'Synchronization complete: {successful} subscription reads succeeded, {failed} failed, {disabled} users disabled, {removed} removed users hidden.',
    config_saved: 'Settings saved.', connection_ok: 'Connection succeeded. {count} clients found.', subscription_ok: ' Subscription test succeeded for {email}; used traffic: {used}.',
    quota_saved: 'Quota saved.', cycle_reset_confirm: 'Reset the Ratio usage cycle for this user?', cycle_reset_done: 'Usage cycle reset.', enforcement_updated: 'Enforcement setting updated.', remote_change_confirm: '{action} this client in 3X-UI?', user_enabled: 'Client enabled.', user_disabled: 'Client disabled.',
    engine_enable_confirm: 'Turn on all Ratio operations?', engine_disable_confirm: 'Pause all Ratio operations? Synchronization, traffic reads, enforcement, quota operations, connection tests, and client status changes will stop.', engine_enabled_toast: 'All Ratio operations are enabled.', engine_disabled_toast: 'All Ratio operations are paused.',
    backup_downloading: 'Creating backup…', backup_downloaded: 'Database backup downloaded.', select_backup: 'Select a database backup file.', type_restore_error: 'Type RESTORE to confirm.', restore_confirm: 'This will replace the current Ratio database. Continue?', restoring: 'Restoring…', restore_done: '{message} Automatic restore point: {point}',
    session_expired: 'Your session has expired.', request_failed: 'Request failed.', no_events: 'No audit events found.', restore_success: 'Database restored successfully.'
  },
  fa: {
    nav_users: 'کاربران', nav_audit: 'لاگ‌ها', nav_connection: 'اتصال', nav_backup: 'پشتیبان‌گیری و بازیابی', sign_out: 'خروج',
    title_users: 'مدیریت کاربران', title_events: 'لاگ‌ها', title_settings: 'اتصال به 3X-UI', title_database: 'پشتیبان‌گیری و بازیابی',
    loading_status: 'در حال دریافت وضعیت…', synchronize: 'همگام‌سازی', engine_loading: 'Ratio…', engine_on: 'Ratio روشن', engine_off: 'Ratio خاموش',
    engine_paused_banner: 'Ratio متوقف است. همگام‌سازی، خواندن ترافیک، تغییر حجم، اعمال محدودیت، تست اتصال و تغییر وضعیت کاربران غیرفعال شده‌اند.',
    total_users: 'کل کاربران', enabled_3xui: 'فعال در 3X-UI', managed_ratio: 'مدیریت‌شده با Ratio', quota_exhausted: 'حجم تمام‌شده',
    search_users: 'جست‌وجوی کاربران…', user: 'کاربر', subscription_usage: 'مصرف لینک ساب', ratio_usage: 'مصرف دوره Ratio', quota: 'حجم', status: 'وضعیت', actions: 'عملیات', loading: 'در حال بارگذاری…',
    select_all_users: 'انتخاب همه کاربران قابل‌نمایش', selected_none: '۰ انتخاب‌شده', selected_count: '{count} انتخاب‌شده', apply_quota_selected: 'اعمال حجم برای انتخاب‌شده‌ها',
    start_selected_enforcement: 'شروع کنترل انتخاب‌شده‌ها', start_selected_confirm: 'کنترل حجم برای کاربران انتخاب‌شده روشن شود؟', start_selected_done: 'کنترل حجم برای {count} کاربر روشن شد. {skipped} کاربر به‌دلیل نداشتن حجم رد شد.',
    theme_toggle_aria: 'تغییر پوسته رنگی', switch_to_light: 'روشن', switch_to_dark: 'تیره',
    stop_all_enforcement: 'توقف کنترل حجم همه کاربران', stop_all_enforcement_confirm: 'کنترل حجم برای همه کاربران فعال Ratio متوقف شود؟ این عملیات هیچ کاربری را در 3X-UI خاموش یا حذف نمی‌کند.', stop_all_enforcement_done: 'کنترل حجم برای {count} کاربر متوقف شد.',
    bulk_quota_title: 'اعمال حجم برای کاربران انتخاب‌شده', selected_users: '{count} کاربر انتخاب‌شده', no_users_selected: 'ابتدا حداقل یک کاربر را انتخاب کنید.', bulk_quota_saved: 'حجم برای {count} کاربر اعمال شد.',
    time: 'زمان', level: 'سطح', event_action: 'عملیات', message: 'پیام', connection_heading: 'اتصال به 3X-UI', connection_note: 'Ratio هیچ‌گاه مستقیماً به دیتابیس 3X-UI متصل نمی‌شود.',
    panel_url: 'آدرس کامل پنل', api_token: 'توکن API', token_placeholder: 'برای حفظ توکن ذخیره‌شده خالی بگذارید', token_help: 'توکن کامل و بدون ماسک را که هنگام ساخت نمایش داده می‌شود وارد کنید.',
    subscription_base: 'آدرس پایه لینک ساب', subscription_help: 'آدرس سرویس ساب را بدون subId کاربر وارد کنید. Ratio شناسه subId هر کاربر را از 3X-UI می‌گیرد و خودکار به انتهای این آدرس اضافه می‌کند.', subid_example: 'SUBID_کاربر',
    poll_interval: 'فاصله بررسی، ثانیه', request_timeout: 'مهلت درخواست، ثانیه', verify_tls: 'بررسی اعتبار گواهی TLS', auto_disable: 'خاموش‌کردن خودکار کاربران پس از اتمام حجم',
    test_connection: 'آزمایش اتصال و لینک ساب', save_settings: 'ذخیره تنظیمات', download_backup: 'دریافت پشتیبان دیتابیس', download_backup_desc: 'یک نسخه سالم SQLite شامل کاربران، حجم‌ها، شمارنده‌های مصرف، گزارش‌ها و تنظیمات رمزنگاری‌شده ایجاد می‌کند.',
    backup_warning: 'فایل پشتیبان شامل تنظیمات حساس رمزنگاری‌شده است. برای بازیابی روی نصب دیگر، همان ENCRYPTION_KEY لازم است.', create_backup: 'ساخت و دانلود پشتیبان',
    import_backup: 'واردکردن پشتیبان دیتابیس', import_backup_desc: 'پشتیبان Ratio را بازیابی می‌کند و قبل از جایگزینی، از دیتابیس فعلی Restore Point می‌سازد.', backup_file: 'فایل پشتیبان', type_restore: 'برای تأیید عبارت', to_confirm: 'را وارد کنید', restore_warning: 'بازیابی، دیتابیس فعلی Ratio را جایگزین می‌کند و به دیتابیس 3X-UI دست نمی‌زند.', restore_button: 'واردکردن و بازیابی دیتابیس',
    set_quota: 'تعیین حجم', new_quota: 'حجم جدید (گیگابایت)', disable_after_quota: 'بعد از اتمام حجم، کاربر خاموش شود', start_new_cycle: 'هم‌اکنون یک دوره مصرف جدید Ratio آغاز شود', cancel: 'انصراف', save_quota: 'ذخیره حجم',
    users_count: '{count} کاربر', no_users: 'کاربری پیدا نشد.', no_subid: 'بدون subId', upload: 'آپلود', download: 'دانلود', total: 'مجموع', unlimited_unknown: 'نامحدود / نامشخص', not_set: 'تعیین نشده', no_ratio_limit: 'بدون محدودیت Ratio', used_percent: '{percent}٪ مصرف‌شده',
    enabled: 'فعال', disabled: 'غیرفعال', enforcement_on: 'کنترل حجم روشن', enforcement_off: 'کنترل حجم خاموش', set_quota_action: 'تعیین حجم', reset_cycle: 'ریست دوره', turn_enforcement_off: 'توقف کنترل', turn_enforcement_on: 'شروع کنترل', enable_user: 'روشن‌کردن', disable_user: 'خاموش‌کردن',
    last_sync: 'آخرین همگام‌سازی', last_attempt: 'آخرین تلاش', no_sync: 'هنوز همگام‌سازی انجام نشده است.', not_configured: 'اتصال 3X-UI تنظیم نشده است.', engine_disabled_caption: 'Ratio متوقف است و همه پردازش‌های عملیاتی خاموش هستند.',
    sync_running: 'در حال همگام‌سازی…', sync_complete: 'همگام‌سازی کامل شد: {successful} لینک ساب موفق، {failed} ناموفق، {disabled} کاربر خاموش و {removed} کاربر حذف‌شده مخفی شد.',
    config_saved: 'تنظیمات ذخیره شد.', connection_ok: 'اتصال موفق بود و {count} کاربر دریافت شد.', subscription_ok: ' لینک ساب کاربر {email} نیز موفق بود؛ مصرف: {used}.',
    quota_saved: 'حجم ذخیره شد.', cycle_reset_confirm: 'دوره مصرف Ratio این کاربر ریست شود؟', cycle_reset_done: 'دوره مصرف ریست شد.', enforcement_updated: 'وضعیت کنترل حجم تغییر کرد.', remote_change_confirm: 'این کاربر در 3X-UI {action} شود؟', user_enabled: 'کاربر روشن شد.', user_disabled: 'کاربر خاموش شد.',
    engine_enable_confirm: 'همه عملکردهای Ratio روشن شوند؟', engine_disable_confirm: 'همه عملکردهای Ratio متوقف شوند؟ همگام‌سازی، خواندن ترافیک، کنترل حجم، تغییر حجم، تست اتصال و تغییر وضعیت کاربران متوقف خواهد شد.', engine_enabled_toast: 'همه عملکردهای Ratio روشن شدند.', engine_disabled_toast: 'همه عملکردهای Ratio متوقف شدند.',
    backup_downloading: 'در حال ساخت پشتیبان…', backup_downloaded: 'پشتیبان دیتابیس دانلود شد.', select_backup: 'یک فایل پشتیبان انتخاب کنید.', type_restore_error: 'برای تأیید، RESTORE را وارد کنید.', restore_confirm: 'دیتابیس فعلی Ratio جایگزین خواهد شد. ادامه می‌دهید؟', restoring: 'در حال بازیابی…', restore_done: '{message} نقطه بازیابی خودکار: {point}',
    session_expired: 'نشست شما منقضی شده است.', request_failed: 'درخواست ناموفق بود.', no_events: 'رویدادی ثبت نشده است.', restore_success: 'دیتابیس با موفقیت بازیابی شد.'
  }
};

const auditTranslations = {
  fa: {
    levels: { info: 'اطلاعات', warning: 'هشدار', error: 'خطا' },
    actions: {
      config_saved: 'ذخیره تنظیمات', engine_enabled: 'روشن‌شدن Ratio', engine_disabled: 'توقف Ratio', quota_changed: 'تغییر حجم', bulk_quota_changed: 'تغییر گروهی حجم', selected_enforcement_started: 'شروع کنترل انتخاب‌شده‌ها',
      cycle_reset: 'ریست دوره', enforcement_changed: 'تغییر کنترل حجم', all_enforcement_stopped: 'توقف کنترل حجم همه کاربران', manual_enable: 'روشن‌کردن دستی', manual_disable: 'خاموش‌کردن دستی',
      remote_users_removed: 'حذف کاربران مبدا', counter_reset: 'ریست شمارنده مبدا', auto_disable: 'خاموش‌سازی خودکار', auto_disable_failed: 'خطای خاموش‌سازی', sync: 'همگام‌سازی', sync_failed: 'خطای همگام‌سازی', database_restored: 'بازیابی دیتابیس'
    },
    messages: {
      'Panel connection settings were saved.': 'تنظیمات اتصال پنل ذخیره شد.', 'Ratio engine was enabled.': 'همه عملکردهای Ratio روشن شدند.', 'Ratio engine was disabled.': 'همه عملکردهای Ratio متوقف شدند.',
      'Ratio quota was updated.': 'حجم Ratio به‌روزرسانی شد.', 'Ratio quota was updated for selected users.': 'حجم Ratio برای کاربران انتخاب‌شده به‌روزرسانی شد.', 'Quota enforcement was started for selected users.': 'کنترل حجم برای کاربران انتخاب‌شده روشن شد.', 'Ratio usage cycle was reset.': 'دوره مصرف Ratio ریست شد.',
      'Quota enforcement setting was updated.': 'تنظیم کنترل حجم به‌روزرسانی شد.', 'Quota enforcement was stopped for all active Ratio users.': 'کنترل حجم برای همه کاربران فعال Ratio متوقف شد.',
      'Client was enabled manually.': 'کاربر به‌صورت دستی روشن شد.', 'Client was disabled manually.': 'کاربر به‌صورت دستی خاموش شد.',
      'Clients removed from 3X-UI were hidden from the active Ratio user list.': 'کاربران حذف‌شده از 3X-UI از فهرست فعال Ratio مخفی شدند.',
      'A source traffic counter reset was detected; the Ratio cycle was preserved.': 'ریست شمارنده ترافیک مبدا تشخیص داده شد و دوره Ratio حفظ شد.',
      'Client was disabled because the Ratio quota was exhausted.': 'کاربر به‌دلیل اتمام حجم Ratio خاموش شد.', 'Automatic client disabling failed.': 'خاموش‌سازی خودکار کاربر ناموفق بود.',
      'Synchronization completed.': 'همگام‌سازی کامل شد.', 'Synchronization completed with errors.': 'همگام‌سازی با خطا پایان یافت.', 'Connection to 3X-UI failed.': 'اتصال به 3X-UI ناموفق بود.',
      'Ratio database was restored from an uploaded backup.': 'دیتابیس Ratio از فایل پشتیبان بازیابی شد.'
    }
  }
};

function auditText(group, value) {
  if (state.lang !== 'fa') return value;
  return auditTranslations.fa[group]?.[value] || value;
}

function t(key, values = {}) {
  let text = translations[state.lang][key] || translations.en[key] || key;
  for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, value);
  return text;
}

function locale() { return state.lang === 'fa' ? 'fa-IR' : 'en-US'; }
function numberText(value, options = {}) { return Number(value || 0).toLocaleString(locale(), options); }
function bytes(value) {
  let number = Number(value || 0);
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let index = 0;
  while (number >= 1024 && index < units.length - 1) { number /= 1024; index += 1; }
  return `${number.toLocaleString(locale(), { maximumFractionDigits: index < 3 ? 0 : 2 })} ${units[index]}`;
}
function dateText(value) {
  if (!value) return '—';
  try { return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)); }
  catch { return value; }
}
function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}
function toast(message, error = false) {
  const element = $('#toast');
  element.textContent = message;
  element.className = `toast show${error ? ' error' : ''}`;
  clearTimeout(element._timer);
  element._timer = setTimeout(() => { element.className = 'toast'; }, 6000);
}
async function api(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined && !(options.body instanceof FormData) && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
  let data = {};
  try { data = await response.json(); } catch {}
  if (response.status === 401) { location = '/login'; throw new Error(t('session_expired')); }
  if (!response.ok || data.ok === false) throw new Error(data.error || data.detail || `HTTP ${response.status}`);
  return data;
}

function isOperational() { return Boolean(state.overview?.config?.engine_enabled); }

function updateThemeButton() {
  const button = $('#theme-toggle');
  if (!button) return;
  const targetLight = state.theme === 'dark';
  button.textContent = `${targetLight ? '☀' : '☾'} ${targetLight ? t('switch_to_light') : t('switch_to_dark')}`;
  button.setAttribute('aria-label', t('theme_toggle_aria'));
}

function applyTheme(theme, persist = true) {
  state.theme = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = state.theme;
  if (persist) localStorage.setItem('ratio-theme', state.theme);
  updateThemeButton();
}

function applyLanguage(lang, persist = true) {
  state.lang = lang === 'fa' ? 'fa' : 'en';
  if (persist) localStorage.setItem('ratio-language', state.lang);
  document.documentElement.lang = state.lang;
  document.documentElement.dir = state.lang === 'fa' ? 'rtl' : 'ltr';
  $$('[data-i18n]').forEach((element) => { element.textContent = t(element.dataset.i18n); });
  $$('[data-i18n-placeholder]').forEach((element) => { element.placeholder = t(element.dataset.i18nPlaceholder); });
  $$('[data-i18n-aria]').forEach((element) => { element.setAttribute('aria-label', t(element.dataset.i18nAria)); });
  $('#language-toggle').textContent = state.lang === 'fa' ? 'English' : 'فارسی';
  updateThemeButton();
  if (state.overview) renderOverview();
  renderUsers();
  updateQuotaModalCopy();
  const active = $('.nav-item[data-view].active');
  if (active) updatePageTitle(active.dataset.view);
  if ($('#view-events').classList.contains('active')) loadEvents();
}

function updateOperationalControls() {
  const operational = isOperational();
  $('#engine-paused-banner').hidden = operational;
  $('#sync-button').disabled = !operational;
  $('#test-config').disabled = !operational;
  $$('[data-operational]').forEach((element) => {
    if (element.id !== 'bulk-quota' && element.id !== 'stop-all-enforcement') element.disabled = !operational;
  });
  updateSelectionUI();
  const stopAll = $('#stop-all-enforcement');
  if (stopAll) stopAll.disabled = !operational || Number(state.overview?.stats?.enforced || 0) === 0;
}

function renderOverview() {
  const data = state.overview;
  if (!data) return;
  $('#stat-total').textContent = numberText(data.stats.total);
  $('#stat-enabled').textContent = numberText(data.stats.enabled);
  $('#stat-enforced').textContent = numberText(data.stats.enforced);
  $('#stat-exhausted').textContent = numberText(data.stats.exhausted);
  const config = data.config;
  if (!config.engine_enabled) {
    $('#sync-caption').textContent = t('engine_disabled_caption');
  } else if (config.last_sync_at) {
    $('#sync-caption').textContent = `${config.last_sync_ok ? t('last_sync') : t('last_attempt')}: ${dateText(config.last_sync_at)}${config.last_error ? ` — ${config.last_error}` : ''}`;
  } else {
    $('#sync-caption').textContent = config.configured ? t('no_sync') : t('not_configured');
  }
  $('#panel-url').value = config.panel_url || '';
  $('#sub-template').value = config.subscription_template || '';
  $('#verify-tls').checked = config.verify_tls;
  $('#auto-disable').checked = config.auto_disable;
  $('#poll-interval').value = config.poll_interval_seconds;
  $('#request-timeout').value = config.request_timeout_seconds;
  const engine = $('#engine-toggle');
  engine.textContent = config.engine_enabled ? t('engine_on') : t('engine_off');
  engine.classList.toggle('engine-on', config.engine_enabled);
  engine.classList.toggle('engine-off', !config.engine_enabled);
  renderUsers();
  updateOperationalControls();
}
function scheduleUiRefresh() {
  clearTimeout(state.refreshTimer);
  const seconds = Math.max(10, Number(state.overview?.config?.poll_interval_seconds || 60));
  state.refreshTimer = setTimeout(async () => {
    try { await Promise.all([loadOverview(), loadUsers()]); }
    catch { scheduleUiRefresh(); }
  }, seconds * 1000);
}
async function loadOverview() {
  state.overview = await api('/api/overview');
  renderOverview();
  scheduleUiRefresh();
}


async function loadUsers() {
  const query = $('#search').value.trim();
  const data = await api(`/api/users${query ? `?q=${encodeURIComponent(query)}` : ''}`);
  state.users = data.users;
  const visibleIds = new Set(state.users.map((user) => user.id));
  state.selectedIds = new Set([...state.selectedIds].filter((id) => visibleIds.has(id)));
  $('#user-count').textContent = t('users_count', { count: numberText(data.users.length) });
  renderUsers();
}

function meterClass(percent) {
  if (percent >= 90) return 'danger';
  if (percent >= 70) return 'warning';
  return 'safe';
}

function subscriptionUsageHtml(user) {
  const total = Number(user.raw_total_bytes || 0);
  const used = Number(user.raw_used_bytes || 0);
  const percent = total > 0 ? Math.min(100, used / total * 100) : 0;
  const numeric = total > 0
    ? `${bytes(used)} / ${bytes(total)} · ${numberText(percent, { maximumFractionDigits: 1 })}%`
    : `${bytes(used)} / ${t('unlimited_unknown')}`;
  return `<div class="subscription-usage">
    <div class="traffic-parts"><span>${t('upload')}: ${bytes(user.raw_upload_bytes)}</span><span>${t('download')}: ${bytes(user.raw_download_bytes)}</span></div>
    <div class="subscription-meter ${meterClass(percent)}" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent.toFixed(1)}"><span style="width:${percent}%"></span></div>
    <div class="subscription-total"><span>${t('total')}</span><strong>${numeric}</strong></div>
  </div>`;
}

function renderUsers() {
  const body = $('#users-body');
  if (!body) return;
  if (!state.users.length) {
    body.innerHTML = `<tr><td colspan="7" class="empty">${t('no_users')}</td></tr>`;
    updateSelectionUI();
    return;
  }
  const operational = isOperational();
  body.innerHTML = state.users.map((user) => {
    const quota = user.quota_bytes;
    const percent = quota ? Math.min(100, user.percent) : 0;
    const status = user.remote_enabled ? `<span class="badge ok">${t('enabled')}</span>` : `<span class="badge off">${t('disabled')}</span>`;
    const control = user.enforcement_enabled ? `<span class="badge ok">${t('enforcement_on')}</span>` : `<span class="badge warn">${t('enforcement_off')}</span>`;
    const disabled = operational ? '' : ' disabled';
    return `<tr class="${state.selectedIds.has(user.id) ? 'selected-row' : ''}">
      <td class="select-column"><input class="user-select" type="checkbox" data-id="${user.id}" ${state.selectedIds.has(user.id) ? 'checked' : ''} aria-label="${esc(user.email)}"></td>
      <td><div class="email">${esc(user.email)}</div><div class="subid">${esc(user.sub_id || t('no_subid'))}</div>${user.last_error ? `<div class="error-text">${esc(user.last_error)}</div>` : ''}</td>
      <td>${subscriptionUsageHtml(user)}</td>
      <td><div class="metric">${bytes(user.cycle_used_bytes)}</div><div class="progress ${percent >= 90 ? 'danger' : ''}"><span style="width:${percent}%"></span></div></td>
      <td><div class="metric">${quota ? bytes(quota) : t('not_set')}</div><small class="muted">${quota ? t('used_percent', { percent: numberText(percent, { maximumFractionDigits: 1 }) }) : t('no_ratio_limit')}</small></td>
      <td><div class="status-stack">${status}${control}</div></td>
      <td><div class="action-grid">
        <button class="btn tiny secondary action-quota" data-action="quota" data-id="${user.id}" data-operational${disabled}>${t('set_quota_action')}</button>
        <button class="btn tiny secondary action-reset" data-action="reset" data-id="${user.id}" data-operational${disabled}>${t('reset_cycle')}</button>
        <button class="btn tiny ${user.enforcement_enabled ? 'warning' : 'success'} action-enforcement" data-action="enforcement" data-id="${user.id}" data-operational${disabled}>${user.enforcement_enabled ? t('turn_enforcement_off') : t('turn_enforcement_on')}</button>
        <button class="btn tiny ${user.remote_enabled ? 'danger' : 'primary'} action-remote" data-action="remote" data-id="${user.id}" data-operational${disabled}>${user.remote_enabled ? t('disable_user') : t('enable_user')}</button>
      </div></td>
    </tr>`;
  }).join('');
  $$('[data-action]').forEach((button) => { button.onclick = () => userAction(button.dataset.action, Number(button.dataset.id)); });
  $$('.user-select').forEach((checkbox) => {
    checkbox.onchange = () => {
      const id = Number(checkbox.dataset.id);
      if (checkbox.checked) state.selectedIds.add(id); else state.selectedIds.delete(id);
      renderUsers();
    };
  });
  updateSelectionUI();
}

function updateSelectionUI() {
  const count = state.selectedIds.size;
  const label = $('#selected-count');
  if (label) label.textContent = count ? t('selected_count', { count: numberText(count) }) : t('selected_none');
  const bulk = $('#bulk-quota');
  if (bulk) bulk.disabled = !isOperational() || count === 0;
  const startSelected = $('#start-selected-enforcement');
  if (startSelected) startSelected.disabled = !isOperational() || count === 0;
  const selectAll = $('#select-all-users');
  if (selectAll) {
    const visible = state.users.map((user) => user.id);
    const checked = visible.length > 0 && visible.every((id) => state.selectedIds.has(id));
    const partiallyChecked = visible.some((id) => state.selectedIds.has(id));
    selectAll.checked = checked;
    selectAll.indeterminate = !checked && partiallyChecked;
  }
}

function updateQuotaModalCopy() {
  const title = $('#quota-modal-title');
  const caption = $('#quota-user');
  if (!title || !caption || !state.quotaTargets.length) return;
  if (state.quotaMode === 'bulk') {
    title.textContent = t('bulk_quota_title');
    caption.textContent = t('selected_users', { count: numberText(state.quotaTargets.length) });
  } else {
    title.textContent = t('set_quota');
    caption.textContent = state.quotaTargets[0].email;
  }
}

function openQuotaTargets(users, mode = 'single') {
  if (!users.length) return;
  state.quotaTargets = users;
  state.quotaMode = mode;
  const first = users[0];
  $('#quota-gb').value = mode === 'single' && first.quota_bytes ? (first.quota_bytes / 1024 ** 3).toFixed(2).replace(/\.00$/, '') : 0;
  $('#quota-enforcement').checked = mode === 'single' ? (first.enforcement_enabled || !first.quota_bytes) : true;
  $('#quota-reset').checked = true;
  updateQuotaModalCopy();
  $('#quota-modal').classList.add('open');
  $('#quota-modal').setAttribute('aria-hidden', 'false');
}
function closeModal() {
  $('#quota-modal').classList.remove('open');
  $('#quota-modal').setAttribute('aria-hidden', 'true');
  state.quotaTargets = [];
  state.quotaMode = 'single';
}

async function userAction(action, id) {
  const user = state.users.find((item) => item.id === id);
  if (!user) return;
  try {
    if (action === 'quota') { openQuotaTargets([user], 'single'); return; }
    if (action === 'reset') {
      if (!confirm(t('cycle_reset_confirm'))) return;
      await api(`/api/users/${id}/reset-cycle`, { method: 'POST' });
      toast(t('cycle_reset_done'));
    } else if (action === 'enforcement') {
      await api(`/api/users/${id}/enforcement`, { method: 'POST', body: JSON.stringify({ enabled: !user.enforcement_enabled }) });
      toast(t('enforcement_updated'));
    } else if (action === 'remote') {
      const enabling = !user.remote_enabled;
      if (!confirm(t('remote_change_confirm', { action: enabling ? t('enable_user') : t('disable_user') }))) return;
      await api(`/api/users/${id}/${enabling ? 'enable' : 'disable'}`, { method: 'POST' });
      toast(enabling ? t('user_enabled') : t('user_disabled'));
    }
    await Promise.all([loadUsers(), loadOverview()]);
  } catch (error) { toast(error.message, true); }
}

async function syncNow() {
  const button = $('#sync-button');
  button.disabled = true;
  button.textContent = t('sync_running');
  try {
    const data = await api('/api/sync', { method: 'POST' });
    toast(t('sync_complete', {
      successful: numberText(data.result.successful), failed: numberText(data.result.failed), disabled: numberText(data.result.disabled), removed: numberText(data.result.removed || 0)
    }), data.result.failed > 0 || Boolean(data.result.disable_error));
    await Promise.all([loadOverview(), loadUsers()]);
  } catch (error) { toast(error.message, true); }
  finally { button.textContent = t('synchronize'); updateOperationalControls(); }
}

function configPayload() {
  return {
    panel_url: $('#panel-url').value.trim(), api_token: $('#api-token').value.trim(), subscription_template: $('#sub-template').value.trim(),
    verify_tls: $('#verify-tls').checked, auto_disable: $('#auto-disable').checked,
    poll_interval_seconds: Number($('#poll-interval').value), request_timeout_seconds: Number($('#request-timeout').value)
  };
}
async function saveConfig(event) {
  event.preventDefault();
  try {
    await api('/api/config', { method: 'POST', body: JSON.stringify(configPayload()) });
    $('#api-token').value = '';
    toast(t('config_saved'));
    await loadOverview();
  } catch (error) { toast(error.message, true); }
}
async function testConfig() {
  const button = $('#test-config');
  button.disabled = true;
  try {
    const data = await api('/api/config/test', { method: 'POST', body: JSON.stringify(configPayload()) });
    let message = t('connection_ok', { count: numberText(data.client_count) });
    if (data.subscription_test) message += t('subscription_ok', { email: data.subscription_test.email, used: bytes(data.subscription_test.used_bytes) });
    toast(message);
  } catch (error) { toast(error.message, true); }
  finally { updateOperationalControls(); }
}
async function toggleEngine() {
  if (!state.overview) return;
  const enabled = !state.overview.config.engine_enabled;
  if (!confirm(enabled ? t('engine_enable_confirm') : t('engine_disable_confirm'))) return;
  const button = $('#engine-toggle');
  button.disabled = true;
  try {
    await api('/api/engine', { method: 'POST', body: JSON.stringify({ enabled }) });
    toast(enabled ? t('engine_enabled_toast') : t('engine_disabled_toast'));
    await Promise.all([loadOverview(), loadUsers()]);
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function stopAllEnforcement() {
  if (!confirm(t('stop_all_enforcement_confirm'))) return;
  const button = $('#stop-all-enforcement');
  button.disabled = true;
  try {
    const data = await api('/api/enforcement/stop-all', { method: 'POST' });
    toast(t('stop_all_enforcement_done', { count: numberText(data.updated) }));
    await Promise.all([loadOverview(), loadUsers()]);
  } catch (error) { toast(error.message, true); }
  finally { updateOperationalControls(); }
}

async function startSelectedEnforcement() {
  const ids = [...state.selectedIds];
  if (!ids.length) { toast(t('no_users_selected'), true); return; }
  if (!confirm(t('start_selected_confirm'))) return;
  const button = $('#start-selected-enforcement');
  button.disabled = true;
  try {
    const data = await api('/api/enforcement/start-selected', {
      method: 'POST',
      body: JSON.stringify({ user_ids: ids })
    });
    toast(t('start_selected_done', {
      count: numberText(data.updated),
      skipped: numberText((data.skipped_no_quota || 0) + (data.skipped_missing || 0))
    }));
    await Promise.all([loadOverview(), loadUsers()]);
  } catch (error) { toast(error.message, true); }
  finally { updateOperationalControls(); }
}

async function loadEvents() {
  try {
    const data = await api('/api/events?limit=200');
    $('#events-body').innerHTML = data.events.length
      ? data.events.map((item) => `<tr><td>${dateText(item.created_at)}</td><td><span class="badge ${item.level === 'error' ? 'off' : item.level === 'warning' ? 'warn' : 'ok'}">${esc(auditText('levels', item.level))}</span></td><td>${esc(auditText('actions', item.action))}</td><td>${esc(item.email || '—')}</td><td>${esc(auditText('messages', item.message))}</td></tr>`).join('')
      : `<tr><td colspan="5" class="empty">${t('no_events')}</td></tr>`;
  } catch (error) { toast(error.message, true); }
}
function filenameFromDisposition(value) {
  const match = /filename\*?=(?:UTF-8''|\")?([^\";]+)/i.exec(value || '');
  return match ? decodeURIComponent(match[1].replace(/\"/g, '')) : '';
}
async function downloadBackup() {
  const button = $('#download-backup');
  button.disabled = true;
  button.textContent = t('backup_downloading');
  try {
    const response = await fetch('/api/database/backup', { method: 'POST', credentials: 'same-origin' });
    if (!response.ok) {
      let message = `HTTP ${response.status}`;
      try { const data = await response.json(); message = data.error || data.detail || message; } catch {}
      throw new Error(message);
    }
    const blob = await response.blob();
    const filename = filenameFromDisposition(response.headers.get('Content-Disposition')) || '3xui-ratio-backup.sqlite3';
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    toast(t('backup_downloaded'));
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = t('create_backup'); }
}
async function restoreBackup() {
  const input = $('#restore-file');
  if (!input.files.length) { toast(t('select_backup'), true); return; }
  if ($('#restore-confirm').value.trim() !== 'RESTORE') { toast(t('type_restore_error'), true); return; }
  if (!confirm(t('restore_confirm'))) return;
  const button = $('#restore-backup');
  const formData = new FormData();
  formData.append('backup', input.files[0]);
  button.disabled = true;
  button.textContent = t('restoring');
  try {
    const data = await api('/api/database/restore', { method: 'POST', body: formData });
    toast(t('restore_done', { message: state.lang === 'fa' ? t('restore_success') : data.message, point: data.restore_point }));
    input.value = '';
    $('#restore-confirm').value = '';
    state.selectedIds.clear();
    await Promise.all([loadOverview(), loadUsers()]);
    if ($('#view-events').classList.contains('active')) await loadEvents();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = t('restore_button'); }
}

function updatePageTitle(name) {
  $('#page-title').textContent = t({ users: 'title_users', events: 'title_events', settings: 'title_settings', database: 'title_database' }[name]);
}
function switchView(name) {
  $$('.view').forEach((view) => view.classList.remove('active'));
  $$('.nav-item[data-view]').forEach((item) => item.classList.toggle('active', item.dataset.view === name));
  $(`#view-${name}`).classList.add('active');
  updatePageTitle(name);
  if (name === 'events') loadEvents();
}

let searchTimer;
document.addEventListener('DOMContentLoaded', async () => {
  applyTheme(localStorage.getItem('ratio-theme') || document.documentElement.dataset.theme || 'dark', false);
  applyLanguage(localStorage.getItem('ratio-language') || (navigator.language?.toLowerCase().startsWith('fa') ? 'fa' : 'en'), false);
  $$('[data-view]').forEach((button) => { button.onclick = () => switchView(button.dataset.view); });
  $$('[data-close]').forEach((button) => { button.onclick = closeModal; });
  $('#quota-modal').onclick = (event) => { if (event.target.id === 'quota-modal') closeModal(); };
  $('#language-toggle').onclick = () => applyLanguage(state.lang === 'fa' ? 'en' : 'fa');
  $('#theme-toggle').onclick = () => applyTheme(state.theme === 'dark' ? 'light' : 'dark');
  $('#engine-toggle').onclick = toggleEngine;
  $('#sync-button').onclick = syncNow;
  $('#config-form').onsubmit = saveConfig;
  $('#test-config').onclick = testConfig;
  $('#download-backup').onclick = downloadBackup;
  $('#restore-backup').onclick = restoreBackup;
  $('#stop-all-enforcement').onclick = stopAllEnforcement;
  $('#start-selected-enforcement').onclick = startSelectedEnforcement;
  $('#bulk-quota').onclick = () => {
    const selected = state.users.filter((user) => state.selectedIds.has(user.id));
    if (!selected.length) { toast(t('no_users_selected'), true); return; }
    openQuotaTargets(selected, 'bulk');
  };
  $('#select-all-users').onchange = (event) => {
    if (event.target.checked) state.users.forEach((user) => state.selectedIds.add(user.id));
    else state.users.forEach((user) => state.selectedIds.delete(user.id));
    renderUsers();
  };
  $('#search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadUsers, 250); };
  $('#quota-form').onsubmit = async (event) => {
    event.preventDefault();
    if (!state.quotaTargets.length) return;
    const payload = {
      quota_gb: Number($('#quota-gb').value),
      enforcement_enabled: $('#quota-enforcement').checked,
      reset_cycle: $('#quota-reset').checked
    };
    try {
      if (state.quotaMode === 'bulk') {
        const data = await api('/api/users/bulk-quota', {
          method: 'POST',
          body: JSON.stringify({ ...payload, user_ids: state.quotaTargets.map((user) => user.id) })
        });
        closeModal();
        state.selectedIds.clear();
        toast(t('bulk_quota_saved', { count: numberText(data.updated) }));
      } else {
        await api(`/api/users/${state.quotaTargets[0].id}/quota`, { method: 'POST', body: JSON.stringify(payload) });
        closeModal();
        toast(t('quota_saved'));
      }
      await Promise.all([loadUsers(), loadOverview()]);
    } catch (error) { toast(error.message, true); }
  };
  try { await Promise.all([loadOverview(), loadUsers()]); } catch (error) { toast(error.message, true); }
});
