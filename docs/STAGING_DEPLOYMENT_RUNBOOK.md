# OpenSEO Staging Deployment Runbook

## 1. Scope & Target Environment
- **Target OS**: Ubuntu 22.04 LTS / 24.04 LTS (Staging Host)
- **Database Engine**: PostgreSQL 16.8 (64-bit)
- **Application Stack**: Python 3.12, FastAPI / Starlette, SQLAlchemy 2.0, Alembic
- **Worker Architecture**: Distributed multi-worker process model with durable database queue (`SELECT ... FOR UPDATE SKIP LOCKED`)
- **Reverse Proxy**: Nginx 1.24+ with TLS 1.3 termination
- **Storage**: Persistent SSD block storage with automated `pg_dump` backups

---

## 2. System Prerequisites & Dependencies

### Operating System Packages
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl gnupg2 lsb-release ca-certificates git build-essential \
                    python3.12 python3.12-venv python3.12-dev libpq-dev nginx
```

### PostgreSQL 16 Installation (Official PGDG Repository)
```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

sudo apt update
sudo apt install -y postgresql-16 postgresql-client-16
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

---

## 3. PostgreSQL Database Configuration

### 3.1 Database & User Creation
Connect as `postgres` superuser:
```bash
sudo -u postgres psql
```
Execute SQL provisioning:
```sql
CREATE ROLE openseo_user WITH LOGIN PASSWORD 'openseo_secure_staging_password_2026';
CREATE DATABASE openseo_staging OWNER openseo_user;
CREATE DATABASE openseo_restore OWNER openseo_user;
GRANT ALL PRIVILEGES ON DATABASE openseo_staging TO openseo_user;
GRANT ALL PRIVILEGES ON DATABASE openseo_restore TO openseo_user;
\q
```

### 3.2 Connection Pooling & Resource Tuning
In `/etc/postgresql/16/main/postgresql.conf`:
```conf
listen_addresses = '127.0.0.1'
port = 5432
max_connections = 100
shared_buffers = 256MB
work_mem = 16MB
maintenance_work_mem = 64MB
wal_level = replica
checkpoint_completion_target = 0.9
```
Reload PostgreSQL:
```bash
sudo systemctl reload postgresql
```

---

## 4. Application Deployment & Environment Setup

### 4.1 Clone Repository & Setup Virtualenv
```bash
sudo mkdir -p /var/www/openseo
sudo chown -R ubuntu:ubuntu /var/www/openseo
cd /var/www/openseo
git clone https://github.com/tungnguyen84/SEO-MACHINE.git .
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.2 Staging Environment File (`.env`)
Create `/var/www/openseo/.env` with strict permissions:
```ini
# Environment
OPENSEO_ENV=staging
APP_ENV=staging

# PostgreSQL 16 Staging Connection
DATABASE_URL=postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging

# Master Cryptographic Keys (Must be 32 bytes hex for AES-256-GCM)
OPENSEO_ENCRYPTION_KEY=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
OPENSEO_JWT_SECRET=super_secret_jwt_staging_signing_key_2026_openseo

# Safety Gates (Strictly enforce non-publishing in Staging)
AUTO_PUBLISH=false
FAIL_ON_UNSUPPORTED_CRITICAL_CLAIM=true
FAIL_ON_UNRESOLVED_DATA_CONFLICT=true
REQUIRE_PRIMARY_EVIDENCE=true
ALLOW_FAKE_TESTING_CLAIMS=false
ALLOW_FAKE_FALLBACK_DATA=false

# Worker Queue Configuration
WORKER_CONCURRENCY=4
JOB_LEASE_SECONDS=30
```
Lock file permissions:
```bash
chmod 600 /var/www/openseo/.env
```

---

## 5. Database Migration Execution (Alembic)

Verify database connectivity and execute schema migrations up to head:
```bash
cd /var/www/openseo
source venv/bin/activate
alembic current
alembic upgrade head
alembic current
```
Expected output:
```
002_durable_jobs (head)
```

---

## 6. Service Supervision (Systemd Units)

### 6.1 API Service (`/etc/systemd/system/openseo-api.service`)
```ini
[Unit]
Description=OpenSEO Staging API Service
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/openseo
EnvironmentFile=/var/www/openseo/.env
ExecStart=/var/www/openseo/venv/bin/uvicorn web.api:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 6.2 Worker Service (`/etc/systemd/system/openseo-worker@.service`)
Allows running multiple concurrent worker processes:
```ini
[Unit]
Description=OpenSEO Staging Background Worker %i
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/openseo
EnvironmentFile=/var/www/openseo/.env
ExecStart=/var/www/openseo/venv/bin/python -m core.jobs.worker --worker-id staging_worker_%i
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now openseo-api
sudo systemctl enable --now openseo-worker@1 openseo-worker@2
```

---

## 7. Reverse Proxy & TLS Configuration (Nginx)

Create `/etc/nginx/sites-available/openseo-staging`:
```nginx
server {
    listen 80;
    server_name staging.openseo.internal;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name staging.openseo.internal;

    ssl_certificate /etc/ssl/certs/openseo-staging.crt;
    ssl_certificate_key /etc/ssl/private/openseo-staging.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy API Traffic
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 10s;
    }
}
```
Enable site and restart Nginx:
```bash
sudo ln -sf /etc/nginx/sites-available/openseo-staging /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 8. Health Check Verification

Test both liveness and readiness endpoints:
```bash
# 1. Liveness Probe (process up)
curl -i https://staging.openseo.internal/health/live
# Expected: HTTP 200 {"status": "LIVE"}

# 2. Readiness Probe (PostgreSQL ping & migration status)
curl -i https://staging.openseo.internal/health/ready
# Expected: HTTP 200 {"status": "READY", "database": "CONNECTED", "migration_head": true}
```

---

## 9. Automated Backup & Disaster Recovery Drill

### 9.1 Daily Backup Command
```bash
mkdir -p /var/backups/openseo
PGPASSWORD=openseo_secure_staging_password_2026 pg_dump \
  -U openseo_user -h 127.0.0.1 -p 5432 \
  -d openseo_staging -F p \
  -f /var/backups/openseo/backup_$(date +%Y%m%d_%H%M%S).sql
```

### 9.2 Restore Drill Procedure
```bash
# 1. Clean restore target
psql -U openseo_user -h 127.0.0.1 -p 5432 -d openseo_restore \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 2. Restore dump file
psql -U openseo_user -h 127.0.0.1 -p 5432 -d openseo_restore \
  -f /var/backups/openseo/backup_latest.sql

# 3. Integrity Check
psql -U openseo_user -h 127.0.0.1 -p 5432 -d openseo_restore \
  -c "SELECT count(*) FROM users; SELECT count(*) FROM site_credentials; SELECT count(*) FROM jobs;"
```

---

## 10. Rollback Procedure

If a deployment or migration fails:
1. **Stop API & Worker**:
   ```bash
   sudo systemctl stop openseo-api openseo-worker@1 openseo-worker@2
   ```
2. **Rollback Database**:
   ```bash
   cd /var/www/openseo
   source venv/bin/activate
   alembic downgrade -1
   ```
   *(Or restore previous SQL backup into `openseo_staging`)*
3. **Revert Git Commit**:
   ```bash
   git checkout HEAD~1
   ```
4. **Restart Services & Verify**:
   ```bash
   sudo systemctl restart openseo-api openseo-worker@1 openseo-worker@2
   curl -f http://127.0.0.1:8000/health/ready
   ```
