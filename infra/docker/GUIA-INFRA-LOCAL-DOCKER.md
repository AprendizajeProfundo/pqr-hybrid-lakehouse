# Guía de Implementación: Infraestructura Local en Docker para PQR Hybrid Lakehouse

**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Basado en:** ADR-0001, ADR-0003, ADR-0004, ADR-0006, ADR-0010, ADR-0012  

Esta guía detalla los pasos para implementar la infraestructura local usando Docker Compose, alineada con la arquitectura por planos (Control/Data/Compute). El setup es K8s-ready (ADR-0012) y facilita migración a AWS (e.g., RDS para Postgres, S3 para storage, ECS/Fargate para compute).

## Prerrequisitos
- Docker >= 20.10
- Docker Compose >= 2.0
- 8GB RAM mínimo (para Dask workers)
- Puerto 80/443 libres (para servicios web)

## Paso 1: Instalar y Verificar Docker
1. Instala Docker Desktop (macOS) o Docker Engine (Linux).
2. Verifica: `docker --version` y `docker-compose --version`.
3. Inicia Docker Desktop si es necesario.

## Paso 2: Crear Estructura de Directorios
Crea la carpeta `infra/local/` en el proyecto:
```
infra/local/
├── docker-compose.yml
├── .env
├── init-scripts/
│   ├── init-postgres.sql
│   └── init-supabase.sh
├── configs/
│   ├── prefect-agent.toml
│   └── grafana-dashboards/
└── volumes/
    ├── postgres-data/
    ├── rustfs-data/
    └── grafana-data/
```

## Paso 3: Configurar Variables de Entorno (.env)
Crea `infra/local/.env`:
```
# Control Plane
POSTGRES_USER=postgres
POSTGRES_PASSWORD=localdev123
POSTGRES_DB=pqr_lakehouse
SUPABASE_URL=http://localhost:5432
SUPABASE_ANON_KEY=local-anon-key

# Data Plane
RUSTFS_ACCESS_KEY=rustfsadmin
RUSTFS_SECRET_KEY=rustfsadmin
RUSTFS_ENDPOINT=http://localhost:9000
BUCKET_NAME=pqr-lakehouse

# Compute Plane
DASK_SCHEDULER_ADDRESS=tcp://scheduler:8786
PREFECT_API_URL=http://localhost:4200/api

# Observability
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
PROMETHEUS_URL=http://localhost:9090

# App Serving
STREAMLIT_PORT=8501
METABASE_PORT=3000

# Local Paths (cambiar en AWS)
DATA_PATH=./volumes
LOGS_PATH=./logs
```

## Paso 4: Crear docker-compose.yml
Crea `infra/local/docker-compose.yml`:
```yaml
version: '3.8'

services:
  # Control Plane: Postgres (Supabase-like)
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ./volumes/postgres-data:/var/lib/postgresql/data
      - ./init-scripts/init-postgres.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - pqr-network

  # Data Plane: RustFS (storage engine)
  rustfs:
    image: rustfs/rustfs:latest            # or build path for your RustFS binary
    container_name: rustfs
    restart: unless-stopped

    ports:
      - "9000:9000"   # S3 API
      # - "9001:9001" # admin/console if provided

    environment:
      RUSTFS_ROOT_USER: ${RUSTFS_ACCESS_KEY}
      RUSTFS_ROOT_PASSWORD: ${RUSTFS_SECRET_KEY}

    volumes:
      - ./volumes/rustfs-data:/data   # consider bind-mount to real disk for prod

    networks:
      - pqr-network

  # Compute Plane: Dask Scheduler
  dask-scheduler:
    image: daskdev/dask:latest
    command: dask-scheduler --host 0.0.0.0 --port 8786
    ports:
      - "8786:8786"
      - "8787:8787"
    networks:
      - pqr-network

  # Compute Plane: Dask Workers
  dask-worker:
    image: daskdev/dask:latest
    command: dask-worker ${DASK_SCHEDULER_ADDRESS} --nprocs 2 --nthreads 1
    depends_on:
      - dask-scheduler
    deploy:
      replicas: 2
    networks:
      - pqr-network

  # Orquestación: Prefect Server
  prefect-server:
    image: prefecthq/prefect:latest
    command: prefect server start --host 0.0.0.0
    environment:
      PREFECT_API_URL: ${PREFECT_API_URL}
    ports:
      - "4200:4200"
    networks:
      - pqr-network

  # Observabilidad: Prometheus
  prometheus:
    image: prom/prometheus
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - pqr-network

  # Observabilidad: Grafana
  grafana:
    image: grafana/grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - ./volumes/grafana-data:/var/lib/grafana
      - ./configs/grafana-dashboards:/var/lib/grafana/dashboards
      - ./configs/grafana-provisioning/datasources:/etc/grafana/provisioning/datasources
      - ./configs/grafana-provisioning/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    networks:
      - pqr-network

  # Serving: Streamlit (Dashboard Ejecutivo)
  streamlit:
    build: ../../apps/dashboard-streamlit  # Asume Dockerfile en apps/
    ports:
      - "${STREAMLIT_PORT}:8501"
    environment:
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
    networks:
      - pqr-network

  # Serving: Metabase (BI Autoservicio)
  metabase:
    image: metabase/metabase
    environment:
      MB_DB_TYPE: postgres
      MB_DB_HOST: postgres
      MB_DB_PORT: 5432
      MB_DB_USER: ${POSTGRES_USER}
      MB_DB_PASS: ${POSTGRES_PASSWORD}
      MB_DB_DBNAME: ${POSTGRES_DB}
    ports:
      - "${METABASE_PORT}:3000"
    depends_on:
      - postgres
    networks:
      - pqr-network

networks:
  pqr-network:
    driver: bridge

volumes:
  postgres-data:
  rustfs-data:
  grafana-data:
```

## Paso 5: Crear Scripts de Inicialización

### init-postgres.sql

Copia el script **completo** desde [GUIDE-Init-Postgres-SQL-Explicacion-Detallada](../../docs/04-guides/GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md).

**Estructura exacta creada:**

#### Schemas (4)
- `meta` — Trazabilidad y calidad
- `bronze` — Eventos normalizados
- `silver` — Datos curados, enriquecidos y dimensiones
- `gold` — KPIs y métricas agregadas

#### Tablas por Schema

**Meta (2 tablas):**
- `meta.etl_runs` — Registro de ejecuciones (con auditoría: executed_by, executor_role, execution_context)
- `meta.data_quality` — Resultados de validaciones

**Bronze (1 tabla):**
- `bronze.pqrs_events` — Evento único para todos los eventos PQRS

**Silver - Tablas de Hechos (3 tablas):**
- `silver.tickets` — Estado actual de cada ticket (desnormalizado)
- `silver.messages` — Histórico de mensajes por ticket
- `silver.status_events` — Histórico de cambios de estado

**Silver - Tablas de Dimensiones (6 tablas):**
- `silver.dim_channel` — Canales de entrada (email, teléfono, portal web, SMS, etc.)
- `silver.dim_geo` — Geografía de Colombia con códigos DANE, coordenadas y geometría PostGIS (regiones, departamentos, municipios)
- `silver.dim_pqrs_type` — Tipos PQRS (P=Petición, Q=Queja, R=Reclamo, S=Sugerencia)
- `silver.dim_priority` — Prioridades (Low, Medium, High, Urgent)
- `silver.dim_status` — Estados del ticket (Open, In Process, Resolved, Closed, Rejected, Escalated)
- `silver.dim_role` — Roles de actores (Citizen, Gestor, Supervisor, Admin)

**Gold (3 tablas de KPIs):**
- `gold.kpi_volume_daily` — Volumen diario por canal + tipo PQRS
- `gold.kpi_backlog_daily` — Pendientes diarios por región + tipo PQRS
- `gold.kpi_sla_daily` — Cumplimiento SLA diario por tipo PQRS

#### Vistas Analíticas (2)
- `silver.v_tickets_open` — Tickets abiertos con estado SLA
- `silver.v_sla_summary` — Resumen de cumplimiento SLA por tipo

#### Elementos Adicionales
- **Índices:** 25+ índices en columnas frecuentes (ticket_id, pqrs_type, status, created_at, region, department_name, city_name, sla_due_at, channel, geo)  
  - geométricos en `dim_geo` permiten análisis geoespacial rápidos (departamento/ciudad).
- **Datos iniciales:** Las 6 tablas de dimensiones se pre-cargan con valores colombianos reales (ciudades, departamentos, tipos PQRS, roles, etc.)
- **Auditoría completa:** Cada tabla tiene `created_at`, `updated_at`, y `meta.etl_runs` captura quién ejecutó (executed_by, executor_role, execution_context)
- **Relaciones:** Foreign keys con ON DELETE CASCADE para integridad
- **Comentarios:** Cada schema, tabla y columna documenta su propósito

**Idempotencia:** Todo usa `IF NOT EXISTS` para ejecutarse múltiples veces sin errores. Los inserts en dimensiones usan `ON CONFLICT DO NOTHING`.

Ubicación: `infra/local/init-scripts/init-postgres.sql`

### 5.2 Preparar Entorno de Streamlit

Nuestro `docker-compose.yml` intenta construir el servicio de Streamlit usando el código fuente en la carpeta `apps/`. Si esta carpeta o el `Dockerfile` no existen, Docker lanzará un error (*failed to read dockerfile*). Vamos a crear los archivos base para evitarlo.

1. **Crea la carpeta de la aplicación desde la raíz de tu proyecto:**
   ```
   mkdir -p apps/dashboard-streamlit
   ```

2. **Crea el archivo `apps/dashboard-streamlit/Dockerfile`:**
   ```dockerfile
   FROM python:3.10-slim

   WORKDIR /app

   # Instalar Streamlit y dependencias analíticas
   RUN pip install --no-cache-dir streamlit pandas

   # Copiar el código fuente
   COPY app.py .

   # Exponer el puerto
   EXPOSE 8501

   # Comando para arrancar el servidor
   CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

3. **Crea un archivo temporal `apps/dashboard-streamlit/app.py`:**
   ```python
   import streamlit as st

   st.set_page_config(page_title="PQR Lakehouse", page_icon="📊", layout="wide")

   st.title("📊 PQR Hybrid Lakehouse - Dashboard")
   st.write("¡El contenedor de Streamlit ha sido construido e iniciado correctamente!")
   ```

## Paso 6: Configurar Prometheus y Grafana

Para que la observabilidad funcione automáticamente ("as-code") sin tener que configurar nada a mano en la interfaz, vamos a configurar Prometheus y aprovisionar Grafana (Data Sources y Dashboards).

### 6.1 Crear archivo prometheus.yml

Crea `infra/local/configs/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'pqr-lakehouse-dev'

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Dask Scheduler (Métricas de Tareas)
  - job_name: 'dask-scheduler'
    scrape_interval: 10s
    static_configs:
      - targets: ['dask-scheduler:8787']
```

*(Nota: Se omiten las métricas de Prefect porque no expone un endpoint de metrics nativo en el puerto 4200, y los workers de Dask se omiten porque requieren descubrimiento de servicios avanzado en Docker Compose para evitar conflictos de round-robin de red).*

### 6.2 Aprovisionar el Data Source en Grafana

Para que Grafana se conecte automáticamente a Prometheus, crea `infra/local/configs/grafana-provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### 6.3 Aprovisionar los Dashboards en Grafana

Para que Grafana lea los JSONs que pongamos en nuestra carpeta local automáticamente, crea `infra/local/configs/grafana-provisioning/dashboards/providers.yml`:

```yaml
apiVersion: 1
providers:
  - name: 'PQR Dashboards'
    orgId: 1
    folder: 'Lakehouse'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

### 6.4 Añadir Dashboards (Opcional)

**No necesitas crear ningún archivo `.json` ahora mismo.** La infraestructura levantará perfectamente sin él.

Más adelante, cuando entres a la interfaz de Grafana y armes tu primer dashboard, puedes exportarlo como JSON y guardarlo en la carpeta `infra/local/configs/grafana-dashboards/`. Gracias a la configuración del paso anterior, Grafana leerá automáticamente cualquier JSON que pongas en esa carpeta cada vez que se reinicie.

## Paso 7: Levantar la Infraestructura
1. Navega a `infra/local/`.
2. Ejecuta: `docker-compose up -d`.
3. Verifica: `docker-compose ps`.
4. Accede:
   - Postgres: `psql -h localhost -U postgres -d pqr_lakehouse`
   - RustFS: http://localhost:9001 (login: rustfsadmin/rustfsadmin)
   - Prefect: http://localhost:4200
   - Grafana: http://localhost:3001 (admin/admin)
   - Streamlit: http://localhost:8501
   - Metabase: http://localhost:3000

## Paso 8: Verificar Conectividad y Migración
- Prueba conexiones desde un contenedor: `docker exec -it <service> bash`.
- Para AWS: Cambia .env con RDS/S3 endpoints, usa ECS para servicios.
- Rutas físicas: Usa variables de entorno (e.g., `S3_BUCKET` en lugar de paths locales).

## Paso 9: Próximos Pasos
- Configura Prefect agents para orquestar pipelines.
- Desarrolla código Python en `apps/pipelines/`.
- Monitorea con Grafana dashboards.

Esta setup es minimalista, escalable y alineada con ADRs. Si encuentras issues, ajusta recursos o versiones.