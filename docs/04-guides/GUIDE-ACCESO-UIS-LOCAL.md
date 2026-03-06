# Guía Rápida: Acceso a UIs y Endpoints Locales

**Versión:** 1.0  
**Fecha:** 2026-03-04  
**Ámbito:** entorno local con Docker Compose (`infra/local`)

Esta guía te dice cómo abrir las interfaces web del stack y qué hacer si alguna falla.

## 1) Antes de abrir UIs

Ejecuta desde:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
```

Verifica que servicios estén arriba:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml ps
```

## 2) URLs de acceso

- Dask Dashboard: `http://localhost:8787`
- Grafana: `http://localhost:3001`
- Metabase: `http://localhost:3000`
- Supabase Studio: `http://localhost:3002`
- Prefect UI: `http://localhost:4200`
- RustFS Console (si tu imagen la soporta): `http://localhost:9001`
- Supabase REST (vía Kong): `http://localhost:8000/rest/v1/`

Adicionales útiles:

- Kong HTTP: `http://localhost:8000`
- Kong HTTPS host: `https://localhost:9443`
- RustFS S3 API: `http://localhost:9000`

## 3) Qué revisar si algo falla

### Caso A: La URL no abre (connection refused)

1. Revisa estado del contenedor:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml ps
```

2. Mira logs del servicio:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml logs --tail=120 <servicio>
```

3. Recrea solo ese servicio:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --force-recreate <servicio>
```

### Caso B: Puerto en uso (`bind: address already in use`)

1. Identifica proceso que ocupa el puerto:

```bash
lsof -nP -iTCP:<puerto> -sTCP:LISTEN
```

2. Libera el puerto o cambia el mapeo en `docker-compose*.yml`.

3. Relevanta:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```

### Caso C: Servicio en `unhealthy`

1. Espera 30-60 segundos (algunos healthchecks tardan).
2. Si persiste, revisa health details:

```bash
docker inspect local-<servicio>-1 --format '{{json .State.Health}}'
```

3. Revisa logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml logs --tail=200 <servicio>
```

### Caso D: Prefect no abre en `4200`

1. Validar binding:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml port prefect-server 4200
```

2. Probar conectividad local:

```bash
nc -vz 127.0.0.1 4200
curl -I http://127.0.0.1:4200
```

3. Reiniciar solo Prefect:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --force-recreate prefect-server
```

### Caso E: Supabase Studio aparece `unhealthy` pero abre

Si `http://localhost:3002` responde (ej. `307` a `/project/default`), Studio está operativo para desarrollo.

Si Studio muestra error al listar tablas (`formattedError`):

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml pull supabase-studio
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --force-recreate supabase-studio
```

Y en navegador haz hard refresh (`Cmd+Shift+R`).

### Caso F: RustFS Console (`9001`) no abre

- Verifica si el puerto está publicado:

```bash
docker compose ps rustfs
```

- Si el puerto está publicado y no abre, tu build de `rustfs` puede no incluir UI web.
- En ese caso usa solo API S3 (`http://localhost:9000`).

## 4) Prueba rápida de endpoints por terminal

```bash
curl -I http://localhost:8787
curl -I http://localhost:3001
curl -I http://localhost:3000
curl -I http://localhost:3002
curl -I http://localhost:4200
curl -I http://localhost:8000/rest/v1/
```

Nota: `3002` puede devolver `307` (normal en Studio).

## 5) Recuperación general del stack

Si hay múltiples fallas al mismo tiempo:

```bash
unset DOCKER_DEFAULT_PLATFORM
docker compose -f docker-compose.yml -f docker-compose.supabase.yml down --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build --remove-orphans
```
