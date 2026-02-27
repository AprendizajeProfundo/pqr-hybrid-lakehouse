# 📋 Guía de Implementación: Infraestructura Local en Docker

**⚠️ Nota:** Esta es la **versión educativa**. Para detalles técnicos profundos, consulta `infra/docker/GUIA-INFRA-LOCAL-DOCKER.md`.

---

**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Basado en:** ADR-0001, ADR-0003, ADR-0004, ADR-0006, ADR-0010, ADR-0012  

Esta guía detalla los pasos para implementar la infraestructura local usando Docker Compose, alineada con la arquitectura por planos (Control/Data/Compute). El setup es K8s-ready (ADR-0012) y facilita migración a AWS (e.g., RDS para Postgres, S3 para storage, ECS/Fargate para compute).

---

## Prerrequisitos

- Docker >= 20.10
- Docker Compose >= 2.0
- 8GB RAM mínimo (para Dask workers)
- Puerto 80/443 libres (para servicios web)

---

## Paso 1: Instalar y Verificar Docker

1. Instala Docker Desktop (macOS) o Docker Engine (Linux).
2. Verifica: `docker --version` y `docker-compose --version`.
3. Inicia Docker Desktop si es necesario.

---

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

---

## Paso 3: Configurar Variables de Entorno (.env)

Crea `infra/local/.env`:

```bash
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

**¿Qué es cada variable?**

- **Control Plane:** Credenciales de PostgreSQL.
- **Data Plane:** Credenciales de acceso al almacenamiento RustFS.
- **Compute Plane:** Direcciones de los coordinadores Dask y Prefect.
- **Observability:** Credenciales y puertos de monitoring.
- **Serving:** Puertos de aplicaciones web.

---

## Paso 4: Crear docker-compose.yml

Crea `infra/local/docker-compose.yml` (ver [GUIDE-Docker-Compose-YML-Explicacion-Paso-a-Paso](./GUIDE-Docker-Compose-YML-Explicacion-Paso-a-Paso.md) para explicación detallada).

El archivo define **8 servicios**:
- **Postgres** (Control Plane)
- **RustFS** (Data Plane)
- **Dask Scheduler + Workers** (Compute Plane)
- **Prefect** (Orquestación)
- **Prometheus + Grafana** (Observabilidad)
- **Streamlit + Metabase** (Serving)

Todos en una **red virtual `pqr-network`** para comunicación interna.

---

## Paso 5: Crear Scripts de Inicialización

### `init-postgres.sql`

Ver [GUIDE-Init-Postgres-SQL-Explicacion-Detallada](./GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md).

Docker ejecuta este script automáticamente al iniciar PostgreSQL.

Crea:
- **4 schemas:** meta, bronze, silver, gold
- **Tablas de metadatos:** etl_runs, data_quality
- **Tablas de datos:** pqrs_events, tickets, messages, status_events, KPIs
- **Índices y vistas** para optimización

---

## Paso 6: Configurar Prometheus y Grafana

### `configs/prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'dask-scheduler'
    static_configs:
      - targets: ['dask-scheduler:8787']
  - job_name: 'prefect-server'
    static_configs:
      - targets: ['prefect-server:4200']
```

**¿Para qué?**

Prometheus **recoge métricas** de los servicios cada 15 segundos. Luego Grafana las visualiza en dashboards.

### `configs/grafana-dashboards/`

Agrega ficheros JSON de dashboards aquí. Ejemplos:
- `volume-daily.json` — gráfico de volumen diario
- `sla-compliance.json` — cumplimiento de SLA
- `backlog-regional.json` — pendientes por región

---

## Paso 7: Levantar la Infraestructura

1. Navega a `infra/local/`:
   ```bash
   cd infra/local/
   ```

2. Levanta los contenedores:
   ```bash
   docker-compose up -d
   ```

3. Verifica el estado:
   ```bash
   docker-compose ps
   ```

   Resultado esperado:
   ```
   NAME               STATUS
   postgres           Up 2 minutes
   rustfs             Up 2 minutes
   dask-scheduler     Up 2 minutes
   dask-worker        Up 2 minutes
   prefect-server     Up 2 minutes
   prometheus         Up 2 minutes
   grafana            Up 2 minutes
   streamlit          Up 2 minutes
   metabase           Up 2 minutes
   ```

---

## Paso 8: Acceder a los Servicios

Una vez levantados, accede a cada servicio:

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| **PostgreSQL** | `psql -h localhost -U postgres -d pqr_lakehouse` | Ver `.env` |
| **RustFS** | http://localhost:9001 | rustfsadmin / rustfsadmin |
| **Dask Dashboard** | http://localhost:8787 | (sin auth) |
| **Prefect Server** | http://localhost:4200 | (sin auth) |
| **Prometheus** | http://localhost:9090 | (sin auth) |
| **Grafana** | http://localhost:3001 | admin / admin |
| **Streamlit** | http://localhost:8501 | (sin auth) |
| **Metabase** | http://localhost:3000 | (primero setup) |

---

## Paso 9: Verificar Conectividad

### Conectar a PostgreSQL

```bash
docker-compose exec postgres psql -U postgres -d pqr_lakehouse
```

Dentro del shell `psql`:
```sql
SELECT * FROM meta.etl_runs;
\dt silver.*        -- listar tablas de Silver
\dn                 -- listar schemas
\q                  -- salir
```

### Listar buckets en RustFS (S3)

```bash
# Instala awscli si no lo tienes
pip install awscliv2

# Configura credenciales locales
aws configure --profile local
# Access Key: rustfsadmin
# Secret Key: rustfsadmin
# Region: us-east-1

# Lista buckets
aws --endpoint-url=http://localhost:9000 --profile local s3 ls
```

### Ver logs de un servicio

```bash
docker-compose logs -f postgres       # Postgres
docker-compose logs -f dask-scheduler # Dask
docker-compose logs -f prefect-server # Prefect
```

---

## Paso 10: Parar la Infraestructura

```bash
docker-compose down
```

**⚠️ Nota:** Los datos persisten en `./volumes/` incluso después de parar.

Para limpiar todo (incluyendo datos):
```bash
docker-compose down -v
```

---

## Paso 11: Próximos Pasos

1. **Generar datos sintéticos:**
   ```bash
   python apps/simulator/generate_pqrs_data.py --config docs/07-config/pqrs_simulation_v1.yaml
   ```

2. **Ejecutar pipelines ETL:**
   - Configura Prefect agents.
   - Crea flows en `apps/pipelines/`.
   - Programa ejecuciones automáticas.

3. **Monitorear en Grafana:**
   - Importa dashboards JSON.
   - Visualiza métricas en tiempo real.

4. **Analizar en Metabase:**
   - Conecta a PostgreSQL Gold.
   - Crea reportes ejecutivos.

---

## Troubleshooting

### Puerto ya en uso
```bash
# Encuentra el proceso usando el puerto
lsof -i :5432

# O cambia en .env a otro puerto
POSTGRES_PORT=5433
```

### Contenedor no arranca
```bash
docker-compose logs <service>
docker-compose up <service>  # Ver logs en tiempo real
```

### Sin acceso a RustFS
- Verifica que rustfs está corriendo: `docker-compose ps rustfs`
- Revisa credenciales en `.env`
- Prueba: `curl -u rustfsadmin:rustfsadmin http://localhost:9000/`  # endpoint S3 de RustFS (ya no existe /minio).

---

## Migración a Producción (AWS)

Cambios necesarios:

| Componente | Local | Producción |
|-----------|-------|------------|
| PostgreSQL | Contenedor | RDS (PostgreSQL managed) |
| Storage | RustFS local | S3 o EBS |
| Compute | Dask local | ECS/Fargate o EC2 |
| Orchestration | Prefect local | Prefect Cloud |
| Monitoring | Prometheus/Grafana | CloudWatch + Grafana Cloud |

**Configuración:**

Actualiza `.env` con endpoints de AWS:
```bash
POSTGRES_HOST=pqr-db.xxxxxx.rds.amazonaws.com
POSTGRES_PORT=5432
RUSTFS_ENDPOINT=https://pqr-lakehouse.s3.amazonaws.com
# etc.
```

---

## Conclusión

Con esta guía tienes una infraestructura local **completa, aislada y reproducible**:

✅ Desarrollo rápido sin depender de cloud.  
✅ Testing de pipelines localmente.  
✅ Listo para migración a Kubernetes/AWS.  
✅ Escalable: agrega workers/réplicas según necesites.

¡A explorar y aprender! 🚀
