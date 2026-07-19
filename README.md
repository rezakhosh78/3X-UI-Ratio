# 3X-UI Ratio

3X-UI Ratio is an independent quota-management panel for **Sanaei 3X-UI**.

It reads users through the official 3X-UI HTTP API, reads traffic from each user's subscription response headers, stores quota state in its own SQLite database, and disables exhausted users through the official API. It never opens or edits the 3X-UI database directly.

## Features

- User synchronization through the current Clients API.
- Compatibility fallback through the legacy Inbounds API.
- Subscription traffic parsing from `Subscription-Userinfo` and `x-subscription-userinfo`.
- Independent Ratio usage cycles that survive traffic resets in 3X-UI.
- Manual and automatic client enable/disable controls.
- SQLite backup download and validated database restore in the Web UI.
- Automatic restore point before every database import.
- English Ubuntu installer and terminal management interface.
- Docker Compose deployment with a non-root application container.

## Version 0.1.2 authentication fix

Some 3X-UI releases intentionally return HTTP 404 for an existing API route when authentication is missing or invalid. Version 0.1.2 sends the AJAX identification header expected by 3X-UI, allowing the server to return HTTP 401 instead. Ratio can now distinguish an invalid API token from a genuinely incorrect API URL.

Use the plaintext API token displayed once when a token is created under the 3X-UI Authentication/API Tokens settings. A masked token copied later cannot authenticate.

## Install on Ubuntu or Debian

Extract the server archive and run:

```bash
cd 3xui-ratio
sudo bash install.sh
```

After installation, open the terminal manager with:

```bash
sudo 3xui-ratio
```

Direct commands:

```bash
sudo 3xui-ratio status
sudo 3xui-ratio start
sudo 3xui-ratio stop
sudo 3xui-ratio restart
sudo 3xui-ratio logs
sudo 3xui-ratio backup
sudo 3xui-ratio update /root/3X-UI-Ratio-v0.1.10.tar.gz
sudo 3xui-ratio uninstall
```

## Configure the 3X-UI connection

Enter the exact URL used to open the 3X-UI panel in a browser, including its WebBasePath, for example:

```text
http://server-ip:2053/secret-path
https://panel.example.com/secret-path
```

Do not manually append `/panel/api`.

Then enter a newly created plaintext API token. Ratio sends it as:

```text
Authorization: Bearer YOUR_TOKEN
```

The supported official API roots include:

```text
<panel-access-url>/panel/api/clients
<panel-access-url>/panel/api/inbounds
```

## Subscription URL template

Examples:

```text
{panel_url}/sub/{sub_id}
https://sub.example.com/sub/{sub_id}
```

Available variables are `{panel_url}`, `{sub_id}`, `{subId}`, and `{email}`.

## Database backup and restore

Open **Backup & Restore** in the Web UI.

- **Create and download backup** creates a consistent SQLite snapshot.
- **Import and restore database** validates the SQLite header, integrity, and required Ratio tables before replacing the current database.
- A pre-restore snapshot is created automatically under `/opt/3xui-ratio/data/backups`.

Backups contain sensitive configuration. Restoring a backup on another installation requires the same `ENCRYPTION_KEY` to decrypt the stored 3X-UI API token.

## Update an existing installation

Copy the new archive to the server, then run:

```bash
sudo 3xui-ratio update /root/3X-UI-Ratio-v0.1.10.tar.gz
```

A full backup is created automatically before the update. Existing `.env`, database, users, quotas, usage counters, and audit records are preserved.

## Security

- Keep `/opt/3xui-ratio/.env` readable only by root.
- Put the Ratio Web UI behind HTTPS before enabling `COOKIE_SECURE=true`.
- Restrict the Ratio port to administrator IP addresses or a reverse proxy.
- API tokens are encrypted in the Ratio database using Fernet.
- Ratio does not connect to the 3X-UI SQLite or PostgreSQL database.

## v0.1.4 synchronization fixes

- Removed clients are archived internally but excluded from the dashboard count and user list.
- Subscription URLs returned directly by the 3X-UI client API are preferred when available.
- On HTTP 404, Ratio retries the standard root subscription route (`/sub/{sub_id}`) in addition to the configured template.
- The first working subscription URL is stored for later synchronizations.
- Subscription errors now include every attempted URL, which helps identify a separate subscription domain, port, or custom URI path.

## v0.1.8 branding and navigation

- Added the 3X-UI Ratio logo to the sign-in page, sidebar brand, browser favicon, and touch icon.
- Moved **Powered By ReZa Kh** directly below **Sign out** in the sidebar.
- Renamed **Audit log** to **Logs**.
- Moved **Logs** directly below **Backup & Restore**.
- Included transparent SVG and PNG logo assets for sharp rendering in light and dark themes.


## v0.1.9 project links

- Added compact GitHub and Telegram icons directly below the **3X-UI Ratio** sidebar title.
- GitHub opens `https://github.com/rezakhosh78/3x-ui-Ratio`.
- Telegram opens `https://t.me/pingplas_channel`.
- Both links open safely in a new tab and adapt to light, dark, LTR, RTL, desktop, and mobile layouts.

## v0.1.10 navigation and sign-in refinements

- Added simple inline icons for **Users**, **Connection**, **Backup & Restore**, and **Logs**.
- Enlarged the sign-in logo and positioned it above the **3X-UI Ratio** title.
- Changed the sign-in subtitle to **3X-UI Independent Quota Management**.
- Set the Persian sign-in subtitle to **مدیریت مستقل حجم 3X-UI**.
- Kept the menu icon layout compatible with light, dark, LTR, RTL, desktop, and mobile views.
- Added compact GitHub and Telegram buttons to the sign-in page with safe new-tab links.

