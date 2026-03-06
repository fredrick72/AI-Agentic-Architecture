# Installing Athena

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, Mac, or Linux)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Internet connection (first run only, to pull images)

## Quick Start

### Windows
Double-click `install.bat` — it will guide you through setup and open Athena in your browser.

### Mac / Linux
```bash
chmod +x install.sh
./install.sh
```

Once running, Athena is at **http://localhost:8080**

---

## Manual Setup

If you prefer to configure manually:

1. Copy `.env.example` to `.env`
2. Open `.env` and set your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```
3. Pull and start:
   ```bash
   docker compose pull
   docker compose up -d
   ```
4. Open http://localhost:8080

---

## Connecting Your Database

Athena connects to your database over the network. Use a **read-only database user** — Athena enforces read-only at the application layer too, but defence in depth is good practice.

| Database     | Connection string format |
|---|---|
| PostgreSQL   | `postgresql://user:pass@host:5432/dbname` |
| MySQL        | `mysql+pymysql://user:pass@host:3306/dbname` |
| SQLite       | `sqlite:///absolute/path/to/file.db` |
| SQL Server   | `mssql+pyodbc://user:pass@host/dbname?driver=ODBC+Driver+17+for+SQL+Server` |

If your database is on the same machine as Athena (running in Docker), use `host.docker.internal` instead of `localhost`.

---

## Stopping Athena

```bash
docker compose down
```

Your data (schema maps, query history) is preserved in Docker volumes. To also delete stored data:

```bash
docker compose down -v
```

---

## Upgrading

```bash
docker compose pull
docker compose up -d
```

---

## Troubleshooting

**Blank screen or connection error**
- Make sure Docker Desktop is running
- Check logs: `docker compose logs -f`

**"Cannot connect to database"**
- Verify your connection string is correct
- If the database is on your local machine, use `host.docker.internal` as the host
- Ensure your database user has SELECT permissions

**Schema shows 0 tables**
- Refresh the page and reconnect — the crawl may still be in progress
- Check schema service logs: `docker compose logs schema-service`
