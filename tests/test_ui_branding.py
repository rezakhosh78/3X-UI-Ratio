from pathlib import Path


def test_sidebar_navigation_and_branding_layout():
    html = Path("app/templates/index.html").read_text(encoding="utf-8")
    assert "/static/ratio-logo.svg" in html
    assert html.index('data-view="database"') < html.index('data-view="events"')
    assert '>Logs<' in html
    assert html.index('data-i18n="sign_out"') < html.index('Powered By <strong>ReZa Kh</strong>')
    assert 'class="app-footer"' not in html
    assert 'href="https://github.com/rezakhosh78/3x-ui-Ratio"' in html
    assert 'href="https://t.me/pingplas_channel"' in html
    assert html.index('class="brand-socials"') > html.index('<strong>3X-UI Ratio</strong>')
    assert html.count('target="_blank"') >= 2
    assert html.count('rel="noopener noreferrer"') >= 2


def test_login_and_favicon_use_ratio_logo():
    login = Path("app/templates/login.html").read_text(encoding="utf-8")
    base = Path("app/templates/base.html").read_text(encoding="utf-8")
    assert 'class="ratio-logo login-logo"' in login
    assert '3X-UI Ratio</h1>' in login
    assert 'rel="icon"' in base and '/static/ratio-logo.svg' in base
    assert Path("app/static/ratio-logo.svg").exists()
    assert Path("app/static/ratio-logo.png").exists()


def test_sidebar_menu_icons_and_login_brand_layout():
    index = Path("app/templates/index.html").read_text(encoding="utf-8")
    login = Path("app/templates/login.html").read_text(encoding="utf-8")
    css = Path("app/static/app.css").read_text(encoding="utf-8")
    assert index.count('class="nav-icon"') == 4
    assert index.index('class="nav-icon"') < index.index('data-i18n="nav_users"')
    assert 'class="ratio-logo login-logo"' in login
    assert login.index('class="ratio-logo login-logo"') < login.index('class="login-brand-title"')
    assert '3X-UI Independent Quota Management' in login
    assert "tagline: 'مدیریت مستقل حجم 3X-UI'" in Path("app/static/login.js").read_text(encoding="utf-8")
    assert '.login-brand-lockup{' in css and 'flex-direction:column' in css
    assert '.login-logo{' in css and 'width:132px' in css


def test_login_project_links_are_present_and_safe():
    login = Path("app/templates/login.html").read_text(encoding="utf-8")
    css = Path("app/static/app.css").read_text(encoding="utf-8")
    assert 'class="login-socials"' in login
    assert 'href="https://github.com/rezakhosh78/3x-ui-Ratio"' in login
    assert 'href="https://t.me/pingplas_channel"' in login
    assert login.count('target="_blank"') >= 2
    assert login.count('rel="noopener noreferrer"') >= 2
    assert 'class="login-social login-social-github"' in login
    assert 'class="login-social login-social-telegram"' in login
    assert '.login-socials{' in css
    assert '.login-social{' in css
