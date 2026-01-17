# 🖥️ Unraid Monitor

> **Discord monitoring bot for Unraid servers with Web UI**

[![Docker Hub](https://img.shields.io/docker/pulls/peterpage2115/unraid-monitor)](https://hub.docker.com/r/peterpage2115/unraid-monitor)
[![Docker Image Size](https://img.shields.io/docker/image-size/peterpage2115/unraid-monitor/latest)](https://hub.docker.com/r/peterpage2115/unraid-monitor)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Docker container that monitors your Unraid server and sends Discord notifications:

- 🌐 **Web Dashboard** - Real-time status view and settings management
- 📊 **Weekly reports** with full server statistics
- 🔍 **Real-time monitoring** of CPU, RAM, disks, temperatures
- 🐳 **Docker container status** tracking (health checks, restarts)
- ⚠️ **Instant alerts** when thresholds are exceeded
- 🎬 **Media service stats** from Radarr, Sonarr, Immich, Jellyfin, qBittorrent

---

## 🆕 What's New in v1.1.0

- **Web UI Dashboard** - Access via `http://your-server:8888`
- **SQLite Database** - Persistent settings storage
- **Plugin Architecture** - Extensible notification system
- **Improved Performance** - Better caching and error handling

---

## 🚀 Quick Start

### 1. Create Discord Webhook

1. Go to your Discord server → **Settings** → **Integrations** → **Webhooks**
2. Click "New Webhook" and copy the URL

### 2. Create `.env` file

```bash
mkdir -p /mnt/user/appdata/unraid-monitor
cd /mnt/user/appdata/unraid-monitor

cat > .env << 'EOF'
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE

# Optional - Your Discord User ID (for @mentions on critical alerts)
DISCORD_USER_ID=

# Optional - Service API Keys
RADARR_URL=http://YOUR_IP:7878
RADARR_API_KEY=

SONARR_URL=http://YOUR_IP:8989
SONARR_API_KEY=

JELLYFIN_URL=http://YOUR_IP:8096
JELLYFIN_API_KEY=

IMMICH_URL=http://YOUR_IP:2283
IMMICH_API_KEY=

QBITTORRENT_URL=http://YOUR_IP:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=

# Optional - Web UI Password (bcrypt hash)
WEB_PASSWORD=
EOF
```

### 3. (Optional) Generate Web UI Password

For secure access to the Web UI dashboard, generate a password hash:

```bash
# Generate password hash
python generate_password.py

# Or use Docker:
docker run --rm peterpage2115/unraid-monitor python generate_password.py

# Add the generated hash to your .env file:
# WEB_PASSWORD=$2b$12$abcd1234...
```

**Note:** If `WEB_PASSWORD` is not set, the Web UI will be accessible without authentication (not recommended for internet-exposed servers).

### 4. Create `docker-compose.yml`

```yaml
services:
  unraid-monitor:
    image: peterpage2115/unraid-monitor:latest
    container_name: unraid-monitor
    restart: unless-stopped
    environment:
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - DISCORD_USER_ID=${DISCORD_USER_ID}
      - TZ=Europe/Warsaw
      - HOST_PROC=/host/proc
      - HOST_SYS=/host/sys
      - WEB_PORT=8888
      - WEB_PASSWORD=${WEB_PASSWORD:-}
      - RADARR_URL=${RADARR_URL}
      - RADARR_API_KEY=${RADARR_API_KEY}
      - SONARR_URL=${SONARR_URL}
      - SONARR_API_KEY=${SONARR_API_KEY}
      - IMMICH_URL=${IMMICH_URL}
      - IMMICH_API_KEY=${IMMICH_API_KEY}
      - JELLYFIN_URL=${JELLYFIN_URL}
      - JELLYFIN_API_KEY=${JELLYFIN_API_KEY}
      - QBITTORRENT_URL=${QBITTORRENT_URL}
      - QBITTORRENT_USERNAME=${QBITTORRENT_USERNAME}
      - QBITTORRENT_PASSWORD=${QBITTORRENT_PASSWORD}
    ports:
      - "8888:8888"  # Web UI
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /mnt/user/appdata/unraid-monitor/data:/app/data
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"
```

**Note on Docker Socket Permissions:**
The container runs as a non-root user (UID 1000) with docker group membership (GID 999). For Docker monitoring to work:
- The Docker socket must be readable by the docker group
- On most systems this is already configured: `ls -l /var/run/docker.sock` should show `srw-rw---- root docker`
- If you encounter permission errors, ensure the socket has group read/write: `sudo chmod 660 /var/run/docker.sock`

### 4. Run

```bash
docker-compose up -d
```

### 5. Access Web UI

Open `http://YOUR_UNRAID_IP:8888` in your browser.

---

## ✨ Features

### Alert Thresholds (defaults)

| Metric | ⚠️ Warning | 🔴 Critical |
|--------|------------|-------------|
| CPU | 80% | 95% |
| RAM | 85% | 95% |
| Disk | 80% | 95% |
| Temperature | 75°C | 90°C |

### Temperature Sensors
By default, only **CPU (coretemp)** and **NVMe** sensors are monitored. Motherboard sensors (AUXTIN, SYSTIN) that often show incorrect values are filtered out.

### Weekly Reports
Sent every **Sunday at 9:00 AM** (configurable) with:
- System overview (CPU, RAM, Storage, Uptime)
- Docker container status
- Media library statistics
- Recent downloads and additions

---

## ⚙️ Configuration

All settings are built into the Docker image with sensible defaults. No configuration files needed!

### Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `DISCORD_WEBHOOK_URL` | ✅ | Discord webhook URL |
| `DISCORD_USER_ID` | ❌ | Your Discord ID for @mentions on critical alerts |
| `TZ` | ❌ | Timezone (default: `Europe/Warsaw`) |
| `WEB_PORT` | ❌ | Web UI port (default: `8888`) |
| `WEB_PASSWORD` | ❌ | Optional password for Web UI |
| `RADARR_URL` | ❌ | Radarr URL (e.g., `http://192.168.1.100:7878`) |
| `RADARR_API_KEY` | ❌ | Radarr API key |
| `SONARR_URL` | ❌ | Sonarr URL |
| `SONARR_API_KEY` | ❌ | Sonarr API key |
| `JELLYFIN_URL` | ❌ | Jellyfin URL |
| `JELLYFIN_API_KEY` | ❌ | Jellyfin API key |
| `IMMICH_URL` | ❌ | Immich URL |
| `IMMICH_API_KEY` | ❌ | Immich API key |
| `QBITTORRENT_URL` | ❌ | qBittorrent URL |
| `QBITTORRENT_USERNAME` | ❌ | qBittorrent username |
| `QBITTORRENT_PASSWORD` | ❌ | qBittorrent password |

---

## 🌐 Web UI

The Web Dashboard provides:

- **Real-time Status** - CPU, RAM, Disk, Temperature at a glance
- **Docker Overview** - Container status with health indicators
- **Service Status** - Connection status to configured services
- **Settings Management** - Adjust thresholds without container restart
- **Actions** - Send test notifications, trigger reports manually
- **Alert History** - View recent alerts and their status

---

## 🔑 Getting API Keys

### Discord Webhook
**Server Settings** → **Integrations** → **Webhooks** → **New Webhook** → **Copy URL**

### Discord User ID
**Enable Developer Mode** → **Right-click your name** → **Copy User ID**

### Radarr / Sonarr
**Settings** → **General** → **API Key**

### Jellyfin
**Dashboard** → **API Keys** → **Add**

### Immich
**Account Settings** → **API Keys** → **New API Key**

### qBittorrent
Just use your login credentials.

---

## 📁 Project Structure

```
unraid-monitor/
├── src/
│   ├── main.py              # Application entry point
│   ├── config.py            # Configuration management
│   ├── discord_client.py    # Discord webhook client (facade)
│   ├── alerts/              # Alert system
│   ├── monitors/            # System & Docker monitors
│   │   └── services/        # Service clients (Radarr, etc.)
│   ├── notifications/       # Notification providers (Discord, etc.)
│   ├── database/            # SQLite settings storage
│   ├── web/                 # FastAPI Web UI
│   │   └── templates/       # HTML templates
│   └── reports/             # Weekly report generator
├── config/
│   └── settings.yaml        # Default settings
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 📜 License

MIT License - feel free to use and modify!

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.
