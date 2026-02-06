# Infrastructure Testing Guide

## Prerequisites Check

Before testing, ensure you have:
- ✅ **Docker Desktop** installed and running
- ✅ **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

### Verify Docker Installation

```bash
# Check Docker is installed
docker --version

# Check Docker is running
docker info

# Expected output: Docker version info and server details
```

If Docker is not found:
1. Download **Docker Desktop** from https://www.docker.com/products/docker-desktop/
2. Install and start Docker Desktop
3. Verify it's running (Docker icon in system tray)

## Step-by-Step Infrastructure Test

### 1. Configure Environment

```bash
cd Demo/

# Windows Command Prompt:
copy .env.example .env
notepad .env

# PowerShell or Git Bash:
cp .env.example .env
```

**Edit `.env` and update this line:**
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

### 2. Start Infrastructure Services

```bash
# Start only infrastructure (no application services yet)
docker compose up -d postgres redis traefik prometheus grafana
```

**Expected output:**
```
[+] Running 5/5
 ✔ Container postgres     Started
 ✔ Container redis        Started
 ✔ Container traefik      Started
 ✔ Container prometheus   Started
 ✔ Container grafana      Started
```

### 3. Wait for Services to Initialize

```bash
# Wait 30 seconds for services to start
# Then check status
docker compose ps
```

**Expected output:**
```
NAME         IMAGE                      STATUS         PORTS
grafana      grafana/grafana:latest     Up (healthy)   0.0.0.0:3000->3000/tcp
postgres     pgvector/pgvector:pg16     Up (healthy)   0.0.0.0:5432->5432/tcp
prometheus   prom/prometheus:latest     Up             0.0.0.0:9090->9090/tcp
redis        redis:7-alpine             Up (healthy)   0.0.0.0:6379->6379/tcp
traefik      traefik:v3.0               Up             0.0.0.0:80->80/tcp, 0.0.0.0:8080->8080/tcp
```

All services should show `Up` status.

### 4. Test PostgreSQL

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d agent_db

# Inside psql, run:
\dt

# Expected output: List of tables including:
#  - conversations
#  - conversation_turns
#  - patients
#  - claims
#  - knowledge_base

# Check patients data
SELECT COUNT(*) FROM patients;

# Expected output: 10

# Check for the 3 Johns (for disambiguation demo)
SELECT patient_id, full_name, last_visit_date
FROM patients
WHERE first_name = 'John';

# Expected output:
#  PAT-12345 | John Smith    | 2024-01-15
#  PAT-67890 | John Doe      | 2023-11-20
#  PAT-24680 | John Williams | 2024-02-05

# Exit psql
\q
```

### 5. Test Redis

```bash
# Connect to Redis
docker compose exec redis redis-cli

# Inside redis-cli, run:
PING

# Expected output: PONG

# Set a test value
SET test "Infrastructure working"
GET test

# Expected output: "Infrastructure working"

# Exit
exit
```

### 6. Test Traefik Dashboard

**Open browser and visit:**
- http://localhost:8080/dashboard/

**Expected:**
- Traefik dashboard loads
- Shows "HTTP Routers" and "HTTP Services" (currently empty - we haven't started app services yet)
- No errors

### 7. Test Prometheus

**Open browser and visit:**
- http://localhost:9090

**Expected:**
- Prometheus UI loads
- Click "Status" → "Targets"
- Should show targets for prometheus, traefik (all may be down since app services aren't running yet)

**Run a test query:**
1. Go to http://localhost:9090/graph
2. Enter query: `up`
3. Click "Execute"
4. Should see metrics for `prometheus` and `traefik` with value `1` (up)

### 8. Test Grafana

**Open browser and visit:**
- http://localhost:3000

**Expected:**
- Grafana login page
- Login with: `admin` / `admin`
- Prompted to change password (can skip for demo)
- Grafana home dashboard loads

**Verify Prometheus datasource:**
1. Click "⚙️ Configuration" → "Data sources"
2. Should see "Prometheus" listed
3. Click "Prometheus"
4. Scroll down and click "Save & Test"
5. Expected: "Data source is working" ✅

### 9. Check Container Logs

```bash
# View logs for all services
docker compose logs

# View logs for specific service
docker compose logs postgres
docker compose logs redis
docker compose logs traefik

# Follow logs in real-time
docker compose logs -f
```

**Expected:** No ERROR messages, only startup logs

### 10. Verify Resource Usage

```bash
# Check container resource usage
docker stats --no-stream
```

**Expected output:**
```
CONTAINER     CPU %    MEM USAGE / LIMIT     MEM %
postgres      0.5%     150MiB / 2GiB         7.5%
redis         0.2%     10MiB / 512MiB        2%
traefik       0.1%     20MiB / 512MiB        4%
prometheus    0.3%     100MiB / 1GiB         10%
grafana       0.4%     80MiB / 1GiB          8%
```

All should have low CPU and reasonable memory usage.

## ✅ Infrastructure Test Checklist

- [ ] Docker is installed and running
- [ ] `.env` file created with OpenAI API key
- [ ] All 5 infrastructure containers started
- [ ] PostgreSQL is healthy and contains 10 patients
- [ ] Redis responds to PING
- [ ] Traefik dashboard accessible at http://localhost:8080
- [ ] Prometheus accessible at http://localhost:9090
- [ ] Grafana accessible at http://localhost:3000
- [ ] Prometheus datasource working in Grafana
- [ ] No ERROR messages in logs

## 🐛 Troubleshooting

### Issue: "Port already in use"

```bash
# Check what's using the port (Windows)
netstat -ano | findstr :5432
netstat -ano | findstr :6379
netstat -ano | findstr :3000

# Stop conflicting service or change port in docker-compose.yml
```

### Issue: "Cannot connect to Docker daemon"

- Start Docker Desktop
- Wait for Docker Desktop to fully start (icon in system tray)
- Try again

### Issue: "postgres | ERROR: database 'agent_db' does not exist"

```bash
# Recreate the database
docker compose down -v
docker compose up -d postgres redis traefik prometheus grafana
```

### Issue: Containers exit immediately

```bash
# Check specific container logs
docker compose logs postgres

# Common fixes:
# 1. Ensure .env has correct values
# 2. Check ports aren't in use
# 3. Restart Docker Desktop
```

## 🧹 Cleanup (if needed)

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v

# Remove everything including images
docker compose down -v --rmi all
```

## ✨ Next Steps

Once infrastructure tests pass:

1. **Build Application Services** (Phase 2-5):
   ```bash
   docker compose up -d --build
   ```

2. **Test End-to-End Scenarios** from [README.md](README.md)

3. **Monitor in Grafana** - View real-time metrics

---

**If all tests pass, infrastructure is ready for application services!** 🚀
