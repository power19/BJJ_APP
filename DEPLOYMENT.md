# Deployment Guide

## Docker Deployment (VPS)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

### Quick Start

```bash
# Clone the repository
git clone <your-repo-url> bjj-app
cd bjj-app

# Start the application
./scripts/deploy.sh up
```

The app will be available at `http://your-server-ip:8000`

### Deployment Commands

```bash
# Build the Docker image
./scripts/deploy.sh build

# Start services
./scripts/deploy.sh up

# Stop services
./scripts/deploy.sh down

# View logs
./scripts/deploy.sh logs

# Check status
./scripts/deploy.sh status

# Update and restart
./scripts/deploy.sh update

# Start with Nginx (production)
./scripts/deploy.sh production
```

### Production Setup with SSL

1. Update `nginx/nginx.conf` with your domain
2. Add SSL certificates to `nginx/ssl/`
3. Uncomment the HTTPS server block in nginx.conf
4. Run: `./scripts/deploy.sh production`

### Environment Configuration

The app uses a configuration file at `config/config.json`. This is created through the web UI setup wizard.

### Automatic Billing

The auto-billing scheduler runs inside the Docker container:
- Runs daily at 6:00 AM (America/Paramaribo timezone)
- Generates invoices for members with recurring memberships
- Ensure the container is always running for billing to work

### Backup

```bash
./scripts/backup.sh
```

Backups are stored in `./backups/` and the last 10 are kept automatically.

---

## Android APK

### Building the APK

1. Open `/android` folder in Android Studio
2. Update server URL in `app/build.gradle`:
   ```gradle
   buildConfigField "String", "SERVER_URL", "\"https://your-vps-url.com\""
   ```
3. Build → Generate Signed APK

### Quick Build (Debug)

```bash
cd android
./gradlew assembleDebug
```

APK location: `android/app/build/outputs/apk/debug/app-debug.apk`

### Features

- WebView app connecting to your server
- NFC support for RFID scanning
- Pull-to-refresh
- Offline-aware

See `android/README.md` for detailed Android instructions.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS Server                           │
│  ┌─────────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │   Nginx     │───▶│  FastAPI    │───▶│   ERPNext      │  │
│  │ (Optional)  │    │  (Docker)   │    │   (External)   │  │
│  └─────────────┘    └─────────────┘    └────────────────┘  │
│        │                   │                               │
│        │                   │                               │
│        ▼                   ▼                               │
│   Port 80/443         Port 8000                            │
└─────────────────────────────────────────────────────────────┘
          │
          │  HTTPS
          ▼
┌─────────────────────┐
│   Android App       │
│   (WebView APK)     │
└─────────────────────┘
```

---

## Troubleshooting

### Container not starting

```bash
# Check logs
docker logs invictus-bjj

# Check if port is in use
netstat -tlnp | grep 8000
```

### Auto-billing not running

1. Ensure container is running: `./scripts/deploy.sh status`
2. Check logs: `./scripts/deploy.sh logs | grep Auto-Billing`
3. Verify APScheduler is installed in container

### Connection refused on Android app

1. Verify server is accessible from device network
2. Check `SERVER_URL` in `app/build.gradle`
3. For debug builds, ensure `usesCleartextTraffic="true"` in AndroidManifest.xml
