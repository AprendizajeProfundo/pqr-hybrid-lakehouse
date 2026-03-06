# Guía: Levantando Servicios Locales (Actualizada)

**Versión:** 2.0  
**Fecha:** 2026-03-04

Esta guía es la entrada rápida para estudiantes.

## Fuente canónica de operación

Usa como referencia principal:

- `docs/04-guides/GUIDE-OPERACION-LOCAL-COMANDOS.md`

Ese documento contiene el paso a paso completo de:

- tareas de una sola vez,
- tareas por sesión,
- arranque base vs arranque con Supabase,
- parada/reinicio,
- recuperación sin borrar datos,
- reset total con borrado de volúmenes,
- escala de Dask (`--scale dask-worker=2`).

## Arranque rápido

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
```

### Modo Base

```bash
docker compose up -d --build
```

### Modo Base + Supabase

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

### Verificación

```bash
docker compose ps
docker compose logs -f postgres
```

## Endpoints

- Prefect: `http://localhost:4200`
- Grafana: `http://localhost:3001`
- Metabase: `http://localhost:3000`
- Dask: `http://localhost:8787`
- RustFS API: `http://localhost:9000`

Con Supabase overlay:

- API/Kong: `http://localhost:8000`
- HTTPS/Kong: `https://localhost:9443`
- Auth: `http://localhost:8000/auth/v1`
- REST: `http://localhost:8000/rest/v1`
- Studio: `http://localhost:3002`

## Importante

- `docker compose down` detiene sin borrar datos.
- `docker compose down -v` borra datos locales (destructivo).
- Si editas `init-scripts/`, no se re-ejecutan sobre una DB ya inicializada salvo reaplicación manual o `down -v`.
