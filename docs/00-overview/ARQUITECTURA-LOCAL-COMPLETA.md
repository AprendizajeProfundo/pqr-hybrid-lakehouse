# Arquitectura Local Completa - PQR Hybrid Lakehouse

**Versión:** 1.0  
**Fecha:** 2026-03-04  
**Ámbito:** ejecución local con Docker Compose (base + Supabase overlay)

## 1. Objetivo del documento

Este documento consolida la arquitectura técnica real del proyecto, su operación local y los criterios mínimos para iniciar desarrollo de forma segura y reproducible.

## 2. Resumen ejecutivo

La arquitectura está organizada por planos:

- **Control Plane:** PostgreSQL + PostGIS, metadatos de corridas ETL, calidad de datos, y serving SQL.
- **Data Plane:** RustFS (S3-compatible) para almacenamiento objeto local.
- **Compute Plane:** Dask scheduler/worker para procesamiento paralelo.
- **Orquestación:** Prefect Server local.
- **Observabilidad:** Prometheus + Grafana.
- **Serving:** Streamlit + Metabase.
- **Supabase local (overlay):** Kong, GoTrue (Auth), PostgREST, Postgres Meta, Studio.

## 3. Componentes y puertos

### 3.1 Stack base (`docker-compose.yml`)

- `postgres` (`postgis/postgis:15-3.4`) -> `5432`
- `rustfs` (`rustfs/rustfs:latest`) -> `9000`, `9001` (si aplica consola)
- `dask-scheduler` (`daskdev/dask:latest`) -> `8786`, `8787`
- `dask-worker` (`daskdev/dask:latest`) -> interno
- `prefect-server` (`prefecthq/prefect:3-latest`) -> `4200`
- `prometheus` (`prom/prometheus`) -> `9090`
- `grafana` (`grafana/grafana`) -> `3001`
- `streamlit` (`local-streamlit`) -> `8501`
- `metabase` (`metabase/metabase`) -> `3000`

### 3.2 Overlay Supabase (`docker-compose.supabase.yml`)

- `kong` (`kong:2.8.1`) -> `8000`, `9443` (host)
- `auth` (`supabase/gotrue:v2.186.0`) -> interno
- `rest` (`postgrest/postgrest:v12.2.3`) -> interno
- `meta` (`supabase/postgres-meta:v0.95.2`) -> interno
- `supabase-studio` (`supabase/studio:2025.10.01-sha-8460121`) -> `3002`

## 4. Diseño por planos

### 4.1 Control Plane

- Base de datos principal: PostgreSQL con PostGIS.
- Esquemas iniciales: `auth`, `meta`, `bronze`, `silver`, `gold`.
- Script de inicialización: `infra/local/init-scripts/init-postgres.sql`.
- Roles Supabase/PostgREST: `infra/local/init-scripts/010-supabase-roles.sql`.
- Clasificación en Silver: tabla `silver.preclassification` (versionado por `run_id` y `model_version`).

### 4.2 Data Plane

- RustFS simula S3 local.
- API S3 en `9000`.
- Persistencia en bind mount local `infra/local/volumes/rustfs-data`.
- La consola `9001` depende del build de la imagen; si responde `501`, no hay UI utilizable.

### 4.3 Compute Plane

- Dask scheduler coordina workers.
- Worker usa `--nworkers 2 --nthreads 1`.
- Escala local por comando (`docker compose up -d --scale dask-worker=2`).

### 4.4 Orquestación

- Prefect Server local en `4200`.
- Imagen fijada a Prefect 3 (`prefecthq/prefect:3-latest`) para evitar incompatibilidad con comandos legacy.

### 4.5 Observabilidad

- Prometheus scrapea métricas base (incluye scheduler Dask).
- Grafana consume Prometheus y dashboards provisionados.

### 4.6 Serving y consumo

- Streamlit para dashboard ejecutivo inicial.
- Metabase para exploración BI.
- Supabase REST en `http://localhost:8000/rest/v1/`.

## 5. Red, persistencia y ciclo de vida

### 5.1 Red

- Red común: `pqr-network` (bridge).
- Todos los servicios comparten resolución por nombre de contenedor.

### 5.2 Persistencia

Bind mounts en `infra/local/volumes/` para:

- `postgres-data`
- `rustfs-data`
- `grafana-data`

### 5.3 Reinicio y logs

- Política `restart: unless-stopped` para servicios.
- Rotación de logs `json-file` (`10m`, `3` archivos).

## 6. Salud y dependencias

- `postgres`: healthcheck con `pg_isready`.
- `dask-scheduler`: healthcheck TCP.
- `prefect-server`: healthcheck TCP.
- `metabase`, `auth`, `rest`, `meta`: dependen de `postgres` healthy.
- `dask-worker`: depende de `dask-scheduler` healthy.
- `supabase-studio`: healthcheck HTTP custom (`/project/default`).

## 7. Variables de entorno críticas

Archivo: `infra/local/.env`

Variables clave:

- DB: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- Supabase: `SUPABASE_URL`, `SUPABASE_API_URL`, `SUPABASE_SITE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_AUTHENTICATOR_PASSWORD`
- OpenAI para Studio assistant: `OPENAI_API_KEY`
- Dask/Prefect: `DASK_SCHEDULER_ADDRESS`, `PREFECT_API_URL`

Regla importante:

- Variables en `.env` deben usar formato `KEY=value` sin espacios alrededor de `=`.

## 8. Flujo de arranque recomendado

```bash
cd infra/local
unset DOCKER_DEFAULT_PLATFORM
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

Verificación:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml ps
```

## 9. Flujo de parada y recuperación

### 9.1 Parada sin pérdida de datos

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml down --remove-orphans
```

### 9.2 Reset total (destructivo)

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml down -v --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

### 9.3 Reaplicar SQL sobre volumen existente

```bash
docker compose exec -T postgres psql -U postgres -d pqr_lakehouse < init-scripts/init-postgres.sql
docker compose exec -T postgres psql -U postgres -d pqr_lakehouse < init-scripts/010-supabase-roles.sql
```

## 10. URLs funcionales de operación

- Prefect: `http://localhost:4200`
- Dask: `http://localhost:8787`
- Grafana: `http://localhost:3001`
- Metabase: `http://localhost:3000`
- Streamlit: `http://localhost:8501`
- Supabase Studio: `http://localhost:3002`
- Supabase REST: `http://localhost:8000/rest/v1/`
- Kong HTTPS host: `https://localhost:9443`
- RustFS API: `http://localhost:9000`
- RustFS console (si soportada): `http://localhost:9001`

## 11. Riesgos conocidos y mitigación

1. **Plataformas mixtas (`arm64/amd64`)**
- Mitigación: plataformas definidas por servicio en Compose; evitar `DOCKER_DEFAULT_PLATFORM` global.

2. **Tags `latest` en parte del stack**
- Riesgo: cambios inesperados de imagen.
- Mitigación: pinnear versiones progresivamente (ya aplicado en componentes Supabase críticos y Prefect).

3. **Supabase Studio `unhealthy` intermitente**
- Si UI responde (`307`/`200`), operativo para dev.
- Mantener healthcheck custom y versión estable.

4. **Errores de permisos OpenAI en Studio assistant**
- Verificar `OPENAI_API_KEY` inyectada y permisos (`api.responses.write`) de la key/proyecto.

## 12. Estado de integridad para iniciar desarrollo

Con la configuración actual, el stack está apto para iniciar desarrollo si se cumple:

- `docker compose ... ps` muestra servicios críticos `Up` y los principales `healthy`.
- endpoints mínimos responden (`4200`, `3001`, `3000`, `8787`, `3002`, `8000/rest/v1/`).
- `PostGIS_Version()` responde y existen esquemas `auth/meta/bronze/silver/gold`.

## 13. Documentos operativos relacionados

- `docs/04-guides/GUIDE-OPERACION-LOCAL-COMANDOS.md`
- `docs/04-guides/GUIDE-LEVANTANDO-SERVICIOS.md`
- `docs/04-guides/GUIDE-ACCESO-UIS-LOCAL.md`
- `docs/04-guides/GUIDE-BAJAR-SUBIR-STACK.md`

## 14. Diagramas PUML (overview)

Los siguientes diagramas PlantUML están en `docs/00-overview/` y están alineados con el estado real de `infra/local/docker-compose.yml` + `infra/local/docker-compose.supabase.yml`:

1. `PUML-ARQ-CONTEXTO-GENERAL.puml`
- Vista macro por planos (control/data/compute/orquestación/observabilidad/serving/supabase).

2. `PUML-ARQ-CONTENEDORES-DETALLE.puml`
- Contenedores Docker, dependencias y relaciones de tráfico interno.

3. `PUML-ARQ-DATOS-ETL.puml`
- Flujo de datos Raw -> Bronze -> Silver -> Gold + trazabilidad en `meta`.

4. `PUML-ARQ-RED-PUERTOS.puml`
- Exposición de puertos host, endpoints locales y mapeo hacia contenedores.

5. `PUML-ARQ-DB-ESQUEMAS.puml`
- Modelo lógico por esquemas PostgreSQL (`auth/meta/bronze/silver/gold`).

6. `PUML-ARQ-OPERACION-SECUENCIA.puml`
- Secuencia operativa de arranque, salud y validación del stack.

## 15. Renderizado de diagramas

Ejemplo con PlantUML CLI (si la tienes instalada):

```bash
cd docs/00-overview
plantuml PUML-ARQ-CONTEXTO-GENERAL.puml
plantuml PUML-ARQ-CONTENEDORES-DETALLE.puml
plantuml PUML-ARQ-DATOS-ETL.puml
plantuml PUML-ARQ-RED-PUERTOS.puml
plantuml PUML-ARQ-DB-ESQUEMAS.puml
plantuml PUML-ARQ-OPERACION-SECUENCIA.puml
```
