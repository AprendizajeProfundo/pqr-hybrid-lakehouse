# Guía Operativa Local: Comandos Canónicos

**Versión:** 2026-03-04 (rev.2)  
**Ámbito:** `infra/local`  
**Objetivo:** levantar, detener, reiniciar y recuperar el stack local sin sorpresas.

## 1) Qué se hace una sola vez

1. Instalar Docker Desktop y dejarlo corriendo.
2. Crear/ajustar `infra/local/.env`.
3. Elegir modo de operación:
- Modo Base: solo `docker-compose.yml`.
- Modo Base + Supabase: `docker-compose.yml` + `docker-compose.supabase.yml`.

## 2) Variables mínimas recomendadas (`infra/local/.env`)

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=localdev123
POSTGRES_DB=pqr_lakehouse

SUPABASE_URL=http://localhost:8000
SUPABASE_API_URL=http://localhost:8000
SUPABASE_SITE_URL=http://localhost:3002
SUPABASE_JWT_SECRET=dev-jwt-secret-change-me-please-32-chars-min
SUPABASE_ANON_KEY=local-anon-key
SUPABASE_SERVICE_ROLE_KEY=local-service-role-key
SUPABASE_DB_AUTHENTICATOR_PASSWORD=authenticator-dev-password

DASK_SCHEDULER_ADDRESS=tcp://dask-scheduler:8786
PREFECT_API_URL=http://localhost:4200/api

STREAMLIT_PORT=8501
METABASE_PORT=3000
```

## 3) Arranque normal (cada sesión)

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
```

### 3.1 Modo Base

```bash
docker compose up -d --build
```

### 3.2 Modo Base + Supabase

> Nota de versionado: en `docker-compose.supabase.yml` los servicios `auth`, `meta` y `supabase-studio` están fijados para evitar sorpresas de `latest`.
> `auth`: `supabase/gotrue:v2.186.0`
> `meta`: `supabase/postgres-meta:v0.95.2`
> `supabase-studio`: `supabase/studio:2025.10.01-sha-8460121`

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

### 3.3 Escalar Dask workers

```bash
docker compose up -d --scale dask-worker=2
```

## 4) Verificación rápida de salud

```bash
docker compose ps
docker compose logs -f postgres
docker compose logs -f dask-scheduler
```

Validaciones de DB:

```bash
docker compose exec postgres psql -U postgres -d pqr_lakehouse -c "SELECT PostGIS_Version();"
docker compose exec postgres psql -U postgres -d pqr_lakehouse -c "SELECT status_code FROM silver.dim_status ORDER BY 1;"
```

## 5) Parar y volver a arrancar sin perder datos

### 5.1 Parar

```bash
docker compose down
```

### 5.2 Arrancar otra vez

Usa el mismo comando del modo que elegiste:

```bash
docker compose up -d --build
```

O con Supabase:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

## 6) Recuperación cuando algo falla

### 6.1 Reinicio de servicios (sin borrar datos)

```bash
docker compose restart
```

Recrear solo un servicio:

```bash
docker compose up -d --force-recreate postgres
```

### 6.2 Reaplicar scripts SQL en una base existente

```bash
docker compose exec -T postgres psql -U postgres -d pqr_lakehouse < init-scripts/init-postgres.sql
docker compose exec -T postgres psql -U postgres -d pqr_lakehouse < init-scripts/010-supabase-roles.sql
```

### 6.3 Reset total (destructivo)

```bash
docker compose down -v
docker compose up -d --build
```

Si usas overlay Supabase, arranca con ambos `-f` tras el `down -v`.

### 6.4 Error: `latest not found` (Supabase)

Si ves errores como:

- `supabase/gotrue:latest: not found`
- `supabase/postgres-meta:latest: not found`

valida que tu `infra/local/docker-compose.supabase.yml` tenga tags fijos válidos y luego ejecuta:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml pull auth meta
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d
```

### 6.5 `prefect-server` reinicia por `docker-compose` no encontrado

Verifica que la imagen sea `prefecthq/prefect:3-latest` en `docker-compose.yml`.
Si ya corregiste el archivo:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --force-recreate prefect-server
```

### 6.6 Apple Silicon y plataformas mixtas

Si un contenedor falla por plataforma (`amd64` vs `arm64`), no fuerces `DOCKER_DEFAULT_PLATFORM` global.
Usa las plataformas definidas por servicio en `docker-compose.yml` y levanta normal:

```bash
unset DOCKER_DEFAULT_PLATFORM
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

### 6.7 Supabase Studio: error al consultar tablas (`formattedError`)

Si Studio muestra:

`No se pudieron recuperar las tablas` y `invalid_type ... formattedError`,

recrea Studio con la versión fija y recarga navegador:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml pull supabase-studio
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --force-recreate supabase-studio
```

Luego haz hard refresh (`Cmd+Shift+R`).

## 7) Endpoints esperados

- Prefect UI: `http://localhost:4200`
- Grafana: `http://localhost:3001`
- Metabase: `http://localhost:3000`
- Dask Dashboard: `http://localhost:8787`
- Postgres: `localhost:5432`
- RustFS API: `http://localhost:9000`

Si usas Supabase overlay:

- Kong/API: `http://localhost:8000`
- Kong HTTPS host: `https://localhost:9443`
- Auth: `http://localhost:8000/auth/v1`
- REST: `http://localhost:8000/rest/v1`
- Studio: `http://localhost:3002`

## 8) Reglas operativas para estudiantes

1. Ejecuta siempre desde `infra/local`.
2. No mezcles en el mismo ciclo `up` base y `up` con overlay sin hacer `down` antes.
3. Para escala local de Dask usa `--scale`, no `deploy.replicas`.
4. `down` conserva datos; `down -v` los elimina.
5. Si cambias scripts de `init-scripts/`, no se reejecutan automáticamente sobre volumen ya inicializado.
6. En Apple Silicon, no fuerces `DOCKER_DEFAULT_PLATFORM` globalmente; la plataforma se controla por servicio en `docker-compose.yml`.
