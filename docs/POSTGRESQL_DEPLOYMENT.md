# Production PostgreSQL Deployment Guide (Ubuntu 22.04 / 24.04 LTS)

> **Mandate**: OpenSEO uses PostgreSQL 15+ in production to eliminate SQLite concurrency bottlenecks and scale background jobs, entity graphs, and GSC telemetry. Follow this verified guide to provision and validate the production database on an Ubuntu host.

---

## 1. PostgreSQL 16 Installation

```bash
# Update repository and install prerequisites
sudo apt-get update && sudo apt-get install -y curl ca-certificates gnupg lsb-release

# Add PostgreSQL official APT repository
sudo install -d /etc/apt/keyrings
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg
echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list

# Install PostgreSQL 16 and client tools
sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-client-16 postgresql-contrib-16

# Verify systemd service status
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl status postgresql --no-pager
```

---

## 2. Database & User Creation

```bash
# Switch to postgres superuser
sudo -i -u postgres psql

# Run inside psql console:
CREATE ROLE openseo_user WITH LOGIN PASSWORD 'YOUR_STRONG_SECURE_PASSWORD';
CREATE DATABASE openseo_production OWNER openseo_user ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8';

# Grant necessary schema privileges
\c openseo_production
GRANT ALL ON SCHEMA public TO openseo_user;
ALTER SCHEMA public OWNER TO openseo_user;

# Exit psql
\q
```

---

## 3. Environment Variables Configuration

In `/opt/openseo/.env` or systemd service environment file:

```bash
# Production Database Connection URI
DATABASE_URL=postgresql://openseo_user:YOUR_STRONG_SECURE_PASSWORD@127.0.0.1:5432/openseo_production

# Connection Pool Limits (Optimized for Async / Multi-worker)
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=25
DB_POOL_TIMEOUT=30

# Application Secret
SECRET_KEY=generate_with_openssl_rand_hex_32
ENVIRONMENT=production
```

---

## 4. Run Alembic Database Migrations

From the project root on the production server:

```bash
# Activate virtual environment
source /opt/openseo/venv/bin/activate

# Validate current alembic head
alembic current

# Run forward migrations to head
alembic upgrade head

# Verify table creation
python -c "
import os
from sqlalchemy import create_engine, inspect
engine = create_engine(os.getenv('DATABASE_URL'))
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Successfully migrated {len(tables)} tables: {tables[:10]}...')
assert 'entities' in tables and 'compatibility_matrix' in tables and 'serp_snapshots' in tables
"
```

---

## 5. Automated Backup & Disaster Recovery

### Automated Nightly Backup Cron
Create `/etc/cron.daily/openseo-postgres-backup`:

```bash
#!/bin/bash
set -euo pipefail
BACKUP_DIR="/var/backups/openseo"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "${BACKUP_DIR}"

# Run pg_dump with custom compressed format
PGPASSWORD="YOUR_STRONG_SECURE_PASSWORD" pg_dump \
  -h 127.0.0.1 \
  -U openseo_user \
  -F c \
  -b \
  -v \
  -f "${BACKUP_DIR}/openseo_backup_${TIMESTAMP}.dump" \
  openseo_production

# Retain only last 30 daily backups
find "${BACKUP_DIR}" -type f -name "openseo_backup_*.dump" -mtime +30 -delete
```

```bash
sudo chmod +x /etc/cron.daily/openseo-postgres-backup
```

### Restore Procedure

```bash
# To restore onto a clean database:
PGPASSWORD="YOUR_STRONG_SECURE_PASSWORD" pg_restore \
  -h 127.0.0.1 \
  -U openseo_user \
  -d openseo_production \
  --clean \
  --if-exists \
  -v \
  /var/backups/openseo/openseo_backup_YYYYMMDD_HHMMSS.dump
```

---

## 6. Connection Pooling via PgBouncer (For High Concurrency)

For setups running multiple crawler workers and API instances:

```bash
# Install PgBouncer
sudo apt-get install -y pgbouncer

# Edit /etc/pgbouncer/pgbouncer.ini:
# [databases]
# openseo_production = host=127.0.0.1 port=5432 dbname=openseo_production
#
# [pgbouncer]
# listen_addr = 127.0.0.1
# listen_port = 6432
# auth_type = scram-sha-256
# auth_file = /etc/pgbouncer/userlist.txt
# pool_mode = transaction
# max_client_conn = 500
# default_pool_size = 20

sudo systemctl enable pgbouncer
sudo systemctl restart pgbouncer
```

---

## 7. Health Check Verification Endpoint

Verify runtime database connectivity with a live query:

```bash
curl -f http://127.0.0.1:8000/api/v1/health/db || echo "Database Health Check Failed"
```

Expected JSON response:
```json
{
  "status": "healthy",
  "database": "postgresql",
  "connection_pool": "connected",
  "readiness": "READY"
}
```
