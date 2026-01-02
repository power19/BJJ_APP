# BJJ App - VPS Deployment Guide

## Prerequisites
- Generate Cloudflare origin certificate for `bjj.powermental.online`
- Access to your VPS

## Step 1: Upload BJJ App to VPS

```bash
# On your local machine, from the BJJ_APP directory:
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  ./ ubuntu@your-vps:/home/ubuntu/docker/bjj-app/
```

Or using scp:
```bash
scp -r ./* ubuntu@your-vps:/home/ubuntu/docker/bjj-app/
```

## Step 2: Create SSL Certificates

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Create certificate for `bjj.powermental.online`
3. Save as:
   - `/home/ubuntu/docker/frappe_docker/cert/bjj.powermental.online.pem`
   - `/home/ubuntu/docker/frappe_docker/cert/bjj.powermental.online.key`

## Step 3: Add Nginx Configuration

Copy the bjj.conf to your nginx configs:
```bash
cp /home/ubuntu/docker/bjj-app/bjj.conf /home/ubuntu/docker/frappe_docker/bjj.conf
```

## Step 4: Update pwd.yml

Add to the `nginx-proxy` volumes section:
```yaml
      - /home/ubuntu/docker/frappe_docker/bjj.conf:/etc/nginx/conf.d/bjj.conf:ro
      - ./cert/bjj.powermental.online.pem:/etc/ssl/cloudflare/bjj.powermental.online.crt:ro
      - ./cert/bjj.powermental.online.key:/etc/ssl/cloudflare/bjj.powermental.online.key:ro
```

Add the bjj-app service:
```yaml
  bjj-app:
    build: /home/ubuntu/docker/bjj-app
    image: bjj-app
    container_name: bjj-app
    restart: always
    environment:
      - TZ=America/Paramaribo
    volumes:
      - bjj-config:/app/config
      - bjj-data:/app/data
```

Add to volumes section at bottom:
```yaml
volumes:
  bjj-config:
  bjj-data:
```

## Step 5: Build and Deploy

```bash
cd /home/ubuntu/docker/frappe_docker

# Build the BJJ app image
docker-compose -f pwd.yml build bjj-app

# Restart nginx-proxy to load new config
docker-compose -f pwd.yml restart nginx-proxy

# Start BJJ app
docker-compose -f pwd.yml up -d bjj-app
```

## Step 6: Configure the App

1. Visit `https://bjj.powermental.online/settings`
2. Configure ERPNext connection:
   - URL: `https://invictus.powermental.online`
   - API Key & Secret from ERPNext

## Step 7: Cloudflare DNS

Add DNS record in Cloudflare:
- Type: A
- Name: bjj
- Content: Your VPS IP
- Proxy: Yes (orange cloud)

## Verify Deployment

```bash
# Check if container is running
docker ps | grep bjj-app

# Check logs
docker logs bjj-app

# Test health
curl http://localhost:8000/
```

## Troubleshooting

### Container not starting
```bash
docker logs bjj-app
```

### Nginx proxy issues
```bash
docker logs nginx-proxy
docker exec nginx-proxy nginx -t
```

### Rebuild after code changes
```bash
docker-compose -f pwd.yml build bjj-app --no-cache
docker-compose -f pwd.yml up -d bjj-app
```
