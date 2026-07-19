<div align="center">

<img src="assets/logo.png" alt="3X-UI Ratio Logo" width="150">

# 3X-UI Ratio

### 3X-UI Independent Quota Management

[![Version](https://img.shields.io/github/v/release/rezakhosh78/3x-ui-Ratio?display_name=tag&style=for-the-badge)](https://github.com/rezakhosh78/3x-ui-Ratio/releases)
[![License](https://img.shields.io/github/license/rezakhosh78/3x-ui-Ratio?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](#-installation)
[![Telegram](https://img.shields.io/badge/Telegram-Channel-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/pingplas_channel)

[فارسی](README_FA.md) · [English](README.md)

</div>

---

## 📌 About

**3X-UI Ratio** is an independent quota-management panel for 3X-UI.

It reads users from the 3X-UI API, obtains each client's traffic usage from the subscription URL, stores quota information in its own database, and can disable a client through the official 3X-UI API when the configured quota is reached.

> 3X-UI Ratio does **not** directly edit the 3X-UI database.

---

## ✨ Features

- 👥 Import and synchronize 3X-UI clients
- 📡 Read upload, download, and total traffic from subscription headers
- 📊 Animated and color-coded usage progress bars
- 🎯 Set an independent quota for each client
- 📴 Automatically disable clients after quota exhaustion
- ▶️ Start or stop quota enforcement
- ⏸️ Global Ratio ON/OFF control
- ☑️ Multi-select users and apply a shared quota
- 🔄 Automatic synchronization with a minimum interval of 10 seconds
- 🧹 Archive clients removed from 3X-UI without losing historical data
- 💾 Download database backups from the Web UI
- 📥 Import and restore database backups
- 📝 Logs and audit history
- 🌐 English and Persian Web UI
- 🌙 Light and dark themes
- 📱 Responsive RTL/LTR interface
- 🐳 Docker-based installation
- 🛠️ Terminal management command: `3xui-ratio`

---

## 🧩 How It Works

```text
3X-UI API
   │
   ├── User list and client status
   │
   ▼
3X-UI Ratio
   │
   ├── Independent quota database
   ├── Subscription usage reader
   ├── Scheduler and enforcement engine
   │
   ▼
3X-UI API
   └── Disable client when quota is reached
```

Traffic usage is calculated from the subscription response headers:

```text
upload + download = used traffic
```

The quota configured in Ratio is independent of the traffic limit configured in 3X-UI.

---

## ✅ Requirements

Recommended environment:

- Ubuntu 20.04, 22.04, or 24.04
- Root or `sudo` access
- Internet access
- A reachable 3X-UI panel
- 3X-UI API credentials or API token
- Subscription service enabled in 3X-UI

Docker and Docker Compose can be installed automatically by the installer when required.

---

## 🚀 One-Line Installation

Run as root:

```bash
bash <(curl -Ls https://raw.githubusercontent.com/rezakhosh78/3x-ui-Ratio/main/install.sh)
```

Alternative command using `sudo`:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/rezakhosh78/3x-ui-Ratio/main/install.sh)"
```

> If your default GitHub branch is not `main`, replace `main` with the correct branch name.

---

## 📦 Manual Installation

Download the latest `tar.gz` file from the [Releases](https://github.com/rezakhosh78/3x-ui-Ratio/releases) page and run:

```bash
tar -xzf 3X-UI-Ratio-*.tar.gz
cd 3xui-ratio
sudo bash install.sh
```

The installer asks for:

- Web UI port
- Administrator username
- Administrator password
- Secure-cookie preference
- Optional update source

---

## 🖥️ Terminal Management

After installation, run:

```bash
sudo 3xui-ratio
```

Available operations include:

```text
1) Service status
2) Start service
3) Stop service
4) Restart service
5) Live logs
6) Create full backup
7) Update panel
8) Edit installation settings
9) Show version
10) Uninstall completely
0) Exit
```

Direct commands:

```bash
sudo 3xui-ratio status
sudo 3xui-ratio start
sudo 3xui-ratio stop
sudo 3xui-ratio restart
sudo 3xui-ratio logs
sudo 3xui-ratio backup
sudo 3xui-ratio update
sudo 3xui-ratio uninstall
```

---

## 🔗 Connecting to 3X-UI

Open **Connection** in the Web UI and enter the complete 3X-UI access URL, including its WebBasePath.

Example:

```text
https://panel.example.com:8443/your-web-base-path
```

Do not manually append `/panel/api` unless your specific installation requires it.

### Subscription Base URL

Enter the subscription-service URL without the client `subId`.

Example:

```text
https://subscription.example.com/sub
```

Ratio appends the client `subId` automatically:

```text
https://subscription.example.com/sub/CLIENT_SUB_ID
```

---

## 🎯 Quota Enforcement

For each client, you can:

- Set or change the quota
- Reset the usage cycle
- Start enforcement
- Stop enforcement
- Enable or disable the 3X-UI client

When enforcement is enabled:

```text
used traffic >= Ratio quota
```

Ratio verifies the client status and sends a disable request through the 3X-UI API.

### Global Controls

- **Ratio ON/OFF:** pauses or resumes all operational functions
- **Stop All Enforcement:** disables quota enforcement without disabling 3X-UI clients
- **Start Enforcement:** enables enforcement for selected clients with a configured quota

---

## 💾 Backup and Restore

The **Backup & Restore** section supports:

- Creating and downloading a database snapshot
- Importing `.db`, `.sqlite`, or `.sqlite3` files
- Validating SQLite integrity before restore
- Creating an automatic restore point before replacement

Backups include:

- Connections
- Managed users
- Quotas
- Usage cycles
- Settings
- Logs
- Audit history

> Store backups securely because they may contain encrypted connection credentials and operational data.

---

## 🔄 Updating

Update using the terminal manager:

```bash
sudo 3xui-ratio update
```

Or provide a release archive:

```bash
sudo 3xui-ratio update /root/3X-UI-Ratio-latest.tar.gz
```

The updater creates a backup before replacing application files.

---

## 🗑️ Uninstallation

Run:

```bash
sudo 3xui-ratio uninstall
```

Complete removal requires explicit confirmation.

Backups may remain in:

```text
/var/backups/3xui-ratio
```

Delete them manually only when they are no longer needed.

---

## 🔐 Security Notes

- Use HTTPS for both the Ratio Web UI and 3X-UI whenever possible.
- Use a strong administrator password.
- Do not publish API tokens, cookies, backup files, or `.env` files.
- Restrict the Web UI port with a firewall or reverse proxy.
- Keep 3X-UI Ratio and 3X-UI updated.
- Test enforcement on a non-critical client before enabling it for all users.
- Review logs after changing API or subscription settings.

---

## 🧯 Troubleshooting

### No compatible API endpoint was found

Check:

- Panel URL and WebBasePath
- HTTP versus HTTPS
- API token or login credentials
- Reverse-proxy routing
- 3X-UI API availability

### Subscription URL returned HTTP 404

Check:

- Subscription service is enabled
- Subscription port and domain are correct
- Subscription Base URL does not include a client `subId`
- The client has a valid `subId`
- Reverse-proxy routing allows `/sub/...`

### Automatic synchronization is delayed

Check:

```bash
sudo 3xui-ratio logs
```

Also verify:

- Ratio is ON
- Polling interval is at least 10 seconds
- Subscription requests are not timing out
- The server clock is correct
- The container is running

---

## 🛣️ Roadmap

- 📈 Historical traffic charts
- 🔔 Telegram notifications
- 🧑‍💼 Multiple administrator accounts
- 🧩 Multiple 3X-UI panel connections
- 📤 CSV export
- 🗓️ Scheduled quota reset policies
- 🔐 Additional authentication options

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

Please avoid including private server addresses, API tokens, user data, or backup databases in issues and pull requests.

---

## 📣 Links

- 🐙 GitHub: [3X-UI Ratio](https://github.com/rezakhosh78/3x-ui-Ratio)
- ✈️ Telegram: [Ping Plus Channel](https://t.me/pingplas_channel)
- 📦 Releases: [Download latest version](https://github.com/rezakhosh78/3x-ui-Ratio/releases)
- 🐛 Issues: [Report a problem](https://github.com/rezakhosh78/3x-ui-Ratio/issues)

---

## ⚖️ Disclaimer

This project is an independent management tool and is not an official component of 3X-UI.

You are responsible for:

- Securing your server
- Protecting credentials and backups
- Verifying API compatibility
- Testing quota enforcement
- Complying with applicable laws and service-provider policies

---

<div align="center">

### Powered By ReZa Kh

⭐ If this project helps you, please give it a star on GitHub.

</div>
