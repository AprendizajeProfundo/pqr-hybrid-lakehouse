# Guía paso a paso: ¿Qué hace nuestro `docker-compose.yml`?

> Actualización 2026-03-04: para operación diaria (arranque/parada/reinicio/recuperación) usa [GUIDE-OPERACION-LOCAL-COMANDOS.md](./GUIDE-OPERACION-LOCAL-COMANDOS.md) como fuente canónica.

Este archivo define la infraestructura local del proyecto usando Docker Compose.

## 1) Estructura actual del archivo

El archivo actual tiene:

- `x-service-defaults`: ancla YAML con defaults comunes (`restart`, `networks`, `logging`).
- `services`: definición de cada contenedor.
- `networks`: red `pqr-network`.
- `volumes`: volúmenes locales del stack.

## 2) Defaults compartidos (`x-service-defaults`)

Se usa para evitar duplicación y aplicar políticas homogéneas:

- reinicio automático (`unless-stopped`),
- red común,
- rotación de logs (`10m`, `3` archivos).

## 3) Servicio por servicio (resumen técnico)

### 3.1 `postgres`

- Imagen: `postgis/postgis:15-3.4`.
- Monta `./init-scripts` en `/docker-entrypoint-initdb.d`.
- Tiene `healthcheck` con `pg_isready`.

### 3.2 `rustfs`

- Almacenamiento S3-compatible.
- Usa bind mount `./volumes/rustfs-data:/data`.

### 3.3 `dask-scheduler` y `dask-worker`

- Scheduler expone `8786` (cluster) y `8787` (dashboard).
- Worker depende del scheduler saludable (`service_healthy`).
- Para escalar workers localmente se usa:

```bash
docker compose up -d --scale dask-worker=2
```

### 3.4 `prefect-server`

- Orquestación local con UI en `4200`.
- Tiene `healthcheck` TCP.

### 3.5 `prometheus` y `grafana`

- Prometheus carga config desde `./configs/prometheus.yml`.
- Grafana persiste datos en `./volumes/grafana-data`.

### 3.6 `streamlit` y `metabase`

- Streamlit se construye desde `apps/dashboard-streamlit`.
- Metabase depende de `postgres` saludable.

## 4) Comportamiento importante para estudiantes

1. `depends_on` con `service_healthy` evita carreras de arranque.
2. `docker compose down` no borra datos.
3. `docker compose down -v` sí borra datos.
4. Los scripts en `init-scripts/` se ejecutan solo en inicialización de volumen.

## 5) Archivo real de referencia

Para ver la versión exacta vigente, usa siempre:

- `infra/local/docker-compose.yml`
