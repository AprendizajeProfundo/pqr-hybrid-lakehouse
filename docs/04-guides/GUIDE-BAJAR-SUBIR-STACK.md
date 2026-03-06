# Guía Rápida: Bajar y Subir Todo el Stack

**Versión:** 1.0  
**Fecha:** 2026-03-04

## 1) Ir al directorio correcto

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
```

## 2) Bajar todo (sin borrar datos)

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml down --remove-orphans
```

## 3) Subir todo

```bash
unset DOCKER_DEFAULT_PLATFORM
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

## 4) Verificar estado

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml ps
```

## 5) Reset total (borra datos locales)

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml down -v --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

## 6) Web UIs y endpoints

- Prefect UI: `http://localhost:4200`
- Dask Dashboard: `http://localhost:8787`
- Grafana: `http://localhost:3001`
- Metabase: `http://localhost:3000`
- Streamlit: `http://localhost:8501`
- Supabase Studio: `http://localhost:3002`
- Kong/API (Supabase): `http://localhost:8000`
- REST API (Supabase/PostgREST): `http://localhost:8000/rest/v1/`
- RustFS S3 API: `http://localhost:9000`
- RustFS Console (si la imagen la soporta): `http://localhost:9001`

## 7) Si algo no abre

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml logs --tail=120 <servicio>
```

Ejemplos de servicio: `prefect-server`, `supabase-studio`, `kong`, `auth`, `dask-worker`, `postgres`, `rustfs`.
