# Guía paso a paso: ¿Qué hace nuestro `docker-compose.yml`?

> Actualización 2026-03-04: para comandos de operación local usa `docs/04-guides/GUIDE-OPERACION-LOCAL-COMANDOS.md`.

Este documento explica el `docker-compose.yml` vigente de `infra/local`.

## 1) Diseño actual

El archivo usa un bloque `x-service-defaults` para consolidar:

- `restart: unless-stopped`
- red compartida `pqr-network`
- política de logs con rotación

Luego define servicios para control/data/compute/observabilidad/serving.

## 2) Puntos clave operativos

- `postgres` (PostGIS) tiene `healthcheck`.
- `dask-worker` depende del scheduler saludable.
- `metabase` depende de `postgres` saludable.
- `prefect-server` tiene `healthcheck` TCP.

## 3) Escala Dask en local

No se usa `deploy.replicas` para Compose local.
Escala recomendada:

```bash
docker compose up -d --scale dask-worker=2
```

## 4) Comandos de validación

```bash
docker compose config
docker compose ps
docker compose logs -f postgres
```

## 5) Referencias

- `docs/04-guides/GUIDE-OPERACION-LOCAL-COMANDOS.md`
- `infra/local/docker-compose.yml`
