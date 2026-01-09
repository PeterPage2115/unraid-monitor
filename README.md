#  Unraid Monitor

**Discord monitoring bot for Unraid servers**

[![Docker Hub](https://img.shields.io/docker/pulls/peterpage2115/unraid-monitor)](https://hub.docker.com/r/peterpage2115/unraid-monitor)
[![Docker Image Size](https://img.shields.io/docker/image-size/peterpage2115/unraid-monitor/latest)](https://hub.docker.com/r/peterpage2115/unraid-monitor)

A Docker container that monitors your Unraid server and sends Discord notifications:
-  **Weekly reports** with full server statistics
-  **Real-time monitoring** of CPU, RAM, disks, temperatures
-  **Docker container status** tracking (health checks, restarts)
-  **Instant alerts** when thresholds are exceeded
-  **Media service stats** from Radarr, Sonarr, Immich, Jellyfin, qBittorrent

---

##  Quick Start

### 1. Create Discord Webhook

1. Go to your Discord server  Settings  Integrations  Webhooks
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
EOF
```

### 3. Create `docker-compose.yml`

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

### 4. Run

```bash
docker-compose up -d
```

---

##  Features

### Alert Thresholds (defaults)
| Metric | Warning | Critical |
|--------|---------|----------|
| CPU | 80% | 95% |
| RAM | 85% | 95% |
| Disk | 80% | 95% |
| Temperature | 75C | 90C |

### Temperature Sensors
By default, only **CPU (coretemp)** and **NVMe** sensors are monitored. Motherboard sensors (AUXTIN, SYSTIN) that often show incorrect values are filtered out.

### Weekly Reports
Sent every **Sunday at 9:00 AM** (configurable) with:
- System overview (CPU, RAM, Storage, Uptime)
- Docker container status
- Media library statistics
- Recent downloads and additions

---

##  Configuration

All settings are built into the Docker image with sensible defaults. No configuration files needed!

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_WEBHOOK_URL` |  | Discord webhook URL |
| `DISCORD_USER_ID` |  | Your Discord ID for @mentions on critical alerts |
| `TZ` |  | Timezone (default: Europe/Warsaw) |
| `RADARR_URL` |  | Radarr URL (e.g., http://192.168.1.100:7878) |
| `RADARR_API_KEY` |  | Radarr API key |
| `SONARR_URL` |  | Sonarr URL |
| `SONARR_API_KEY` |  | Sonarr API key |
| `JELLYFIN_URL` |  | Jellyfin URL |
| `JELLYFIN_API_KEY` |  | Jellyfin API key |
| `IMMICH_URL` |  | Immich URL |
| `IMMICH_API_KEY` |  | Immich API key |
| `QBITTORRENT_URL` |  | qBittorrent URL |
| `QBITTORRENT_USERNAME` |  | qBittorrent username |
| `QBITTORRENT_PASSWORD` |  | qBittorrent password |

---

##  Getting API Keys

### Discord Webhook
Server Settings  Integrations  Webhooks  New Webhook  Copy URL

### Discord User ID
Enable Developer Mode  Right-click your name  Copy User ID

### Radarr / Sonarr
Settings  General  API Key

### Jellyfin
Dashboard  API Keys  Add

### Immich
Account Settings  API Keys  New API Key

### qBittorrent
Just use your login credentials

---

##  Project Structure

```
unraid-monitor/
 src/
    main.py              # Application entry point
    config.py            # Configuration management
    discord_client.py    # Discord webhook client
    alerts/              # Alert system
    monitors/            # System & Docker monitors
       services/        # Service clients (Radarr, etc.)
    reports/             # Weekly report generator
 config/
    settings.yaml        # Default settings
 Dockerfile
 docker-compose.yml
 requirements.txt
 README.md
```

---

##  License

MIT License - feel free to use and modify!

---

##  Contributing

Pull requests are welcome! For major changes, please open an issue first.
