# GUIA-DISEÑO-e-INFRA

## Introducción

Este repositorio presenta un **MVP de Lakehouse híbrido para PQRS** con enfoque académico: enseñar arquitectura de datos moderna, operación reproducible y diseño cloud-native sin depender de infraestructura compleja en la primera fase.

La solución separa responsabilidades en planos (Control, Data y Compute), define contratos y decisiones de arquitectura vía ADR, y materializa una infraestructura local con Docker Compose que simula un entorno de producción.

Esta guía resume el proyecto en dos partes para uso docente:

1. Diseño arquitectónico.
2. Implementación de infraestructura.

---

## Parte I. Diseño Arquitectónico

## 1) Propósito del sistema

El sistema modela el ciclo PQRS (Peticiones, Quejas, Reclamos y Sugerencias) desde eventos sintéticos, transformándolos en capas analíticas para métricas operativas, SLA y tableros ejecutivos.

Objetivos formativos:

- Comprender arquitectura híbrida por planos.
- Practicar lakehouse por capas (Raw, Bronze, Silver, Gold).
- Aplicar principios de reproducibilidad e idempotencia.
- Integrar observabilidad desde el inicio.

Referencias:

- `docs/00-overview/SYSTEM-OVERVIEW.md`
- `docs/00-overview/SYSTEM-OVERVIEW-V0011.md`

## 2) Arquitectura por planos

La arquitectura central (ADR-0001) define:

- **Control Plane:** PostgreSQL/Supabase-like para metadatos (`meta.*`), estado operativo y serving (`gold_*`).
- **Data Plane:** RustFS (S3-compatible) como fuente histórica de verdad.
- **Compute Plane:** Dask Distributed como motor principal; DuckDB como motor analítico complementario.
- **Orquestación:** Prefect Server.
- **Observabilidad:** Prometheus + Grafana.
- **Serving:** Streamlit (curado ejecutivo) + Metabase (autoservicio BI).

Referencias:

- `docs/02-adr/ADR-0001-Arquitectura-hibrida-por-planos.md`
- `docs/01-architecture/C4-CONTAINERS.puml`
- `docs/01-architecture/C4-CONTEXT_V2.puml`

## 3) Flujo de datos y semántica de capas

Flujo lógico:

1. Generación/ingesta de eventos Raw (JSONL).
2. Transformación estructural a Bronze (Parquet tipado).
3. Curación/enriquecimiento semántico en Silver.
4. Agregaciones de negocio en Gold.
5. Carga de Gold a PostgreSQL para consumo BI.

Reglas clave:

- Raw es append-only e inmutable.
- No mezclar transformación estructural con semántica IA.
- Gold es la API analítica oficial para dashboards.

Referencias:

- `docs/02-adr/ADR-0002-Lakehouse-layout-formatos-particionado.md`
- `docs/02-adr/ADR-0007-Separacion-Estructura-vs-Semántica-IA-en-Silver.md`
- `docs/02-adr/ADR-0010-Estrategia-carga-serving-en-Postgres-Gold-only.md`

## 4) Gobierno, calidad y reproducibilidad

El diseño exige trazabilidad por corrida:

- `run_id`, `seed`, `manifest`, hashes y particionado por `run_id`.
- Registro de calidad y ejecución en `meta.etl_runs` y `meta.data_quality`.
- Política de checks por capa con fallos críticos tipo fail-fast.

Esto permite:

- Re-ejecutar sin duplicar datos (idempotencia).
- Auditar resultados entre corridas.
- Explicar resultados en contexto académico y técnico.

Referencias:

- `docs/02-adr/ADR-0008-Reproducibilidad-idempotencia-por-run_id-seed-manifest+hashes.md`
- `docs/02-adr/ADR-0009-Contratos-de-datos-y-versionamiento-de-esquema.md`
- `docs/02-adr/ADR-0011-Estrategia-calidad-de-datos-checks-por-capa+política-fallo.md`

## 5) Contratos y configuración del dominio PQRS

El repositorio incluye piezas clave para gobernanza de dominio:

- Esquema Raw JSON (`data/contracts/v1/RAW-PQRS.schema.json`).
- Especificaciones Bronze/Silver/Gold (`data/contracts/v1/*.md`).
- Configuración de simulación (`docs/07-config/pqrs_simulation_v1.yaml`).
- Modelo formal de estados (`docs/07-config/pqrs_status_v1.yaml`, ADR-0017).
- Reglas de preclasificación (`docs/07-config/pqrs_preclass_rules_v1.yaml`, ADR-0018).

Estos artefactos son útiles para laboratorios de:

- Validación de esquema.
- Diseño de reglas de clasificación.
- Cálculo de SLA por máquina de estados.

## 6) Roadmap arquitectónico

La línea evolutiva está explícita:

- Fase MVP: Compose + Parquet + Dask + gobernanza base.
- Fase 2: Lakehouse transaccional (Iceberg/Delta), mayor escalamiento.
- Fase 3: Industrialización multi-tenant, seguridad avanzada, streaming y MLOps.

Referencias:

- `docs/02-adr/ADR-0013-No utilizar-Iceberg-Delta Lake-Hudi-en-MVP.md`
- `docs/02-adr/ADR-0014-fase-2-evolucion-lakehouse.md`
- `docs/02-adr/ADR-0015-fase-3-industrializacion.md`

---

## Parte II. Implementación de Infraestructura

## 1) Estado implementado en el repositorio

La infraestructura local está implementada y documentada en:

- `infra/local/docker-compose.yml`
- `infra/local/init-scripts/init-postgres.sql`
- `infra/local/configs/prometheus.yml`
- `infra/local/configs/grafana-provisioning/**`
- `infra/local/configs/grafana-dashboards/pqr-lakehouse-monitoring.json`

Guías de despliegue:

- `docs/04-guides/GUIDE-Implementacion-Infra-Local-Docker.md`
- `infra/docker/GUIA-INFRA-LOCAL-DOCKER.md`
- `docs/04-guides/GUIDE-MIGRATION-LOCAL-TO-CLOUD.md`

## 2) Servicios Docker por función

`docker-compose.yml` levanta los componentes principales:

- `postgres` (Control Plane, puerto 5432).
- `rustfs` (Data Plane S3, puerto 9000).
- `dask-scheduler` (8786/8787) y `dask-worker` (Compute).
- `prefect-server` (4200).
- `prometheus` (9090).
- `grafana` (3001 externo -> 3000 interno).
- `streamlit` (8501 por variable).
- `metabase` (3000 por variable).

Todos conectados por red `pqr-network`.

## 3) Inicialización de base de datos

El script `init-postgres.sql` crea:

- Esquemas: `meta`, `bronze`, `silver`, `gold`.
- Trazabilidad: `meta.etl_runs`, `meta.data_quality`.
- Tablas de dominio: eventos, tickets, mensajes, estados.
- KPIs Gold: volumen, backlog, SLA.
- Dimensiones (canal, geografía, tipo PQRS, prioridad, estado, rol).
- Vistas útiles para análisis y seguimiento de SLA.

Aspectos pedagógicos valiosos:

- Uso de `IF NOT EXISTS` e inserciones idempotentes.
- Índices y comentarios extensivos.
- Diseño analítico con componentes de gobierno integrados.

## 4) Observabilidad as-code

La observabilidad no está “manual”, está versionada:

- Prometheus scrapea su propio endpoint y el scheduler de Dask.
- Grafana se aprovisiona por archivos YAML.
- Dashboards JSON viven dentro del repositorio.

Esto facilita:

- Replicabilidad en clase.
- Demostraciones de SLO/SLA.
- Troubleshooting guiado por métricas.

## 5) Variables de entorno y operación

La operación depende de `.env` en `infra/local/` para:

- Credenciales Postgres y RustFS.
- Endpoint de Prefect y puertos de serving.
- Credenciales de Grafana.

Comandos operativos típicos:

- `docker-compose up -d`
- `docker-compose ps`
- `docker-compose logs -f <servicio>`
- `docker-compose down`

## 6) Migración local a cloud (enfoque conceptual)

La guía de migración mapea 1:1 los componentes:

- Postgres local -> RDS/Aurora.
- RustFS local -> S3.
- Dask en Compose -> ECS/EKS.
- Prefect Server local -> Prefect Cloud o despliegue administrado.
- Prometheus/Grafana locales -> servicios managed.

La idea central para estudiantes:

- **No cambia el modelo mental ni el código de negocio; cambian los endpoints y la plataforma de ejecución.**

## 7) Hallazgos sobre madurez actual

Fortalezas del repositorio:

- Arquitectura bien justificada (ADRs completos).
- Infraestructura local concreta y reproducible.
- Contratos y configuración de dominio bien definidos.

Brechas actuales (importantes para el curso):

- En `apps/` y `scripts/` predominan READMEs; faltan implementaciones de pipelines/simulador/tests en código ejecutable.
- Se recomienda mantener revisión continua de contratos para evitar drift documental entre capas y guías.

---

## Conclusiones

El repositorio es una base sólida para enseñar **arquitectura de datos moderna** y **despliegue de infraestructura local cloud-like**. El diseño está técnicamente bien orientado: separación por planos, lakehouse disciplinado, gobierno de datos y observabilidad integrados.

Para uso docente, su mayor valor está en:

- Mostrar una arquitectura realista sin complejidad excesiva.
- Permitir discusión de decisiones técnicas con soporte formal (ADRs).
- Conectar teoría (diseño) con práctica operativa (Compose + monitoreo + modelo de datos).

Como siguiente nivel académico, la prioridad es completar implementación ejecutable de `apps/` y alinear contratos/documentación menores para cerrar la brecha entre “arquitectura diseñada” y “arquitectura operando end-to-end”.
