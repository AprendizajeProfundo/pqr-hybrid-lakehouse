# Guía Metabase - Dashboard Ejecutivo PQRS (Profesional)

## 0. Conexión primero (obligatorio)
Antes de copiar consultas SQL, confirma que Metabase esté consultando la base correcta.

Parámetros de conexión (entorno local de este proyecto):
1. Host: `postgres`
2. Puerto: `5432`
3. Base de datos: `pqr_lakehouse`
4. Usuario: `postgres`
5. Contraseña: `localdev123`

Si conectas desde terminal local (no desde contenedor):
1. `postgresql://postgres:localdev123@127.0.0.1:5432/pqr_lakehouse`

Pasos en Metabase:
1. `Admin -> Databases`.
2. Crear/editar conexión a `pqr_lakehouse` con esos datos.
3. Ejecutar `Sync database schema now`.
4. En el SQL editor seleccionar esa DB, no `Sample Database`.

Prueba rápida en Metabase SQL:
```sql
SELECT current_database();
SELECT COUNT(*) FROM analytics.v_timeseries_national_daily;
```

## 1. Objetivo
Construir un dashboard serio y útil para operación y dirección, basado en `analytics.*`.

Fuente SQL:
- `apps/dashboard-streamlit/sql/metabase_dashboard_queries.sql`

## 2. Estructura recomendada del dashboard
## Fila 1 (KPIs)
1. Volumen total nacional.
2. Variación promedio diaria (%).
3. SLA promedio (%).
4. Backlog total.

## Fila 2 (Tendencias)
1. Serie nacional por tipo PQRS (líneas).
2. Serie comparativa por departamento (líneas).

## Fila 3 (Gestión territorial)
1. Ranking departamentos por volumen (barras).
2. Ranking departamentos por backlog (barras).
3. SLA por departamento (barras).

## Fila 4 (Geoespacial y detalle)
1. Mapa departamental (pin map con lat/lon y métricas).
2. Tabla detalle ejecutiva.

## 3. Filtros globales del dashboard
Crear y vincular estos filtros:
1. `date_from` (fecha inicio).
2. `date_to` (fecha fin).
3. `pqrs_type` (multiselección).
4. `channel` (multiselección).
5. `department_name` (multiselección).

## 4. Pasos exactos en Metabase
1. Entrar a `http://localhost:3000`.
2. Verificar conexión a DB `pqr_lakehouse`.
3. Crear colección: `PQRS - Ejecutivo`.
4. Para cada bloque SQL (Q1..Q12), crear `Nueva pregunta` -> `SQL`.
5. Guardar cada pregunta con nombre claro:
- `KPI - Volumen Nacional`
- `Serie - Nacional por Tipo`
- `Mapa - Departamental`
- etc.
6. Crear dashboard nuevo: `PQRS Ejecutivo Operativo`.
7. Agregar preguntas al dashboard en el orden sugerido.
8. Agregar filtros globales y mapear variables SQL.
9. Configurar visualizaciones:
- Serie: líneas.
- Ranking: barras horizontales.
- Mapa: pin map (lat/lon).
- Tabla: detalle con orden descendente por `day`.

## 5. Convenciones para un resultado profesional
1. Unidades claras (`%`, conteos).
2. Colores estables por tipo PQRS (`P`, `Q`, `R`, `S`).
3. Evitar mezclar métricas de distintas escalas en un mismo eje.
4. Incluir siempre rango de fechas visible en el encabezado.
5. Mostrar última actualización (`meta.etl_runs`) en una tarjeta auxiliar.

## 6. Consulta auxiliar recomendada (timestamp última corrida)
```sql
SELECT
  run_id,
  started_at,
  finished_at,
  status,
  executed_by
FROM meta.etl_runs
ORDER BY started_at DESC
LIMIT 1;
```

## 7. Criterio de aceptación del dashboard
1. Responde en pocos segundos para filtros típicos.
2. Cambios de filtros actualizan todas las tarjetas correctamente.
3. Mapa y rankings concuerdan con series temporales para el mismo rango.
4. Stakeholders pueden identificar:
- picos,
- zonas críticas,
- incumplimiento SLA,
- evolución por tipo PQRS.
