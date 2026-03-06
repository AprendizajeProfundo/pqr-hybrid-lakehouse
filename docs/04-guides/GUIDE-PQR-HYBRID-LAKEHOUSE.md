# Manual Completo del Proyecto PQR Hybrid Lakehouse

Esta guía organiza el recorrido completo del proyecto para una persona que inicia desde cero y quiere llegar hasta despliegue en AWS.

## 1. Indice rapido
1. Arquitectura y principios: [ARCH-PRINCIPLES](../01-architecture/ARCH-PRINCIPLES.md), [ADR-0001](../02-adr/ADR-0001-Arquitectura-hibrida-por-planos.md), [Guia AWS principiantes](GUIDE-MIGRACION-AWS-PRINCIPIANTES.md)
2. Preparacion del entorno local: [Makefile](../../Makefile), [environment.yml](../../environment.yml), [docker-compose local](../../infra/local/docker-compose.yml), [Guia infra local](GUIDE-Implementacion-Infra-Local-Docker.md)
3. Datos y simulacion: [Documento base](../05-general-docs/Proyecto_PQR_Documento_Inicial_v_0010.pdf), [simulator](../../apps/simulator), [Guia simulacion](GUIDE-GENERACION-SIMULACION-PQRS.md), [Guia JSONL a plataforma](GUIDE-ETL-DESDE-JSONL-A-PLATAFORMA.md)
4. ETL y gobierno: [Guia ETL y Prefect](GUIDE-ETL-POR-ETAPAS-Y-ORQUESTACION-PREFECT.md), [Comandos ETL](GUIDE-COMANDOS-ETL-RAPIDO.md), [Guia init SQL](GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md)
5. Visualizacion y dashboards: [dashboard-streamlit](../../apps/dashboard-streamlit), [Guia dashboard app](GUIDE-DASHBOARD-Y-APP-ANALITICA-PQRS.md), [Guia Metabase](GUIDE-METABASE-DASHBOARD-EJECUTIVO-PQRS.md), [SQL Metabase](../../apps/dashboard-streamlit/sql/metabase_dashboard_queries.sql)
6. Migracion y nube: [Guia deploy AWS](GUIDE-DEPLOY-AWS.md), [Guia Terraform baseline](GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md), [Guia local a cloud](GUIDE-MIGRATION-LOCAL-TO-CLOUD.md), [infra/aws/terraform](../../infra/aws/terraform)
7. Operacion y seguridad: [Guia operacion local](GUIDE-OPERACION-LOCAL-COMANDOS.md), [Guia secretos](GUIDE-SEGURIDAD-SECRETS.md), [CI workflow](../../.github/workflows/ci.yml), [env ejemplo local](../../infra/local/.env.example)
8. Gobernanza y readiness: [Template acta](TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md), [Acta 2026-03-06](ACTA-VALIDACION-PRE-NUBE-2026-03-06.md)

## 2. Arquitectura y principios
- Plano de control: Postgres/Supabase para metadatos y serving. Referencias: [ARCH-PRINCIPLES](../01-architecture/ARCH-PRINCIPLES.md), [ADR-0001](../02-adr/ADR-0001-Arquitectura-hibrida-por-planos.md), [ADR-0016](../02-adr/ADR-0016-Base-Seguimiento-PQRS+Datos-Sintéticos-S3-(RustFS)-para-Analítica-Lakehouse.md).
- Plano de datos: lakehouse en RustFS/S3 por capas. Referencias: [ADR-0002](../02-adr/ADR-0002-Lakehouse-layout-formatos-particionado.md), [Guia infra local](GUIDE-Implementacion-Infra-Local-Docker.md).
- Principios de calidad y reproducibilidad: [ADR-0008](../02-adr/ADR-0008-Reproducibilidad-idempotencia-por-run_id-seed-manifest+hashes.md), [ADR-0011](../02-adr/ADR-0011-Estrategia-calidad-de-datos-checks-por-capa+política-fallo.md).

## 3. Inicio local desde cero
1. Preparar entorno: ejecuta `make env` y valida con `make test` usando [Makefile](../../Makefile).
2. Levantar infraestructura local: usa [docker-compose local](../../infra/local/docker-compose.yml) con [Guia infra local](GUIDE-Implementacion-Infra-Local-Docker.md) y [Guia operacion](GUIDE-OPERACION-LOCAL-COMANDOS.md).
3. Configurar variables: crea `infra/local/.env` desde [env ejemplo local](../../infra/local/.env.example) y aplica [Guia secretos](GUIDE-SEGURIDAD-SECRETS.md).

## 4. Datos, simulacion y ETL
- Simulacion de datos: [script generador](../../apps/simulator/generate_pqrs_data.py), [Guia simulacion](GUIDE-GENERACION-SIMULACION-PQRS.md).
- ETL por etapas: [Guia ETL y Prefect](GUIDE-ETL-POR-ETAPAS-Y-ORQUESTACION-PREFECT.md), [Comandos ETL](GUIDE-COMANDOS-ETL-RAPIDO.md).
- Orquestacion: [prefect_etl_flow.py](../../apps/pipelines/prefect_etl_flow.py).
- Esquema y carga SQL: [init scripts](../../infra/local/init-scripts), [Guia init SQL](GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md).

## 5. Dashboards y analitica
- App ejecutiva: [app.py](../../apps/dashboard-streamlit/app.py), [Guia dashboard app](GUIDE-DASHBOARD-Y-APP-ANALITICA-PQRS.md).
- BI autoservicio: [SQL Metabase](../../apps/dashboard-streamlit/sql/metabase_dashboard_queries.sql), [Guia Metabase](GUIDE-METABASE-DASHBOARD-EJECUTIVO-PQRS.md).
- KPI y mapas: [Guia KPI y mapas](GUIDE-PLAN-ANALITICA-KPI-Y-MAPAS-PQRS.md).

## 6. Ruta a AWS
1. Conceptual: [Guia local a cloud](GUIDE-MIGRATION-LOCAL-TO-CLOUD.md) y [Guia AWS principiantes](GUIDE-MIGRACION-AWS-PRINCIPIANTES.md).
2. Implementacion IaC: [Guia deploy AWS](GUIDE-DEPLOY-AWS.md), [Guia Terraform baseline](GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md), [infra/aws/terraform](../../infra/aws/terraform).
3. Validacion previa: [Template acta](TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md) y [Acta actual](ACTA-VALIDACION-PRE-NUBE-2026-03-06.md).
4. CI minima: [workflow CI](../../.github/workflows/ci.yml).

## 7. Checklist antes de migrar
- Ejecutar tests y validaciones (`make test`, `terraform fmt`, `terraform validate`).
- Verificar secrets fuera de git con [Guia secretos](GUIDE-SEGURIDAD-SECRETS.md).
- Cerrar checklist Go/No-Go de [Guia deploy AWS](GUIDE-DEPLOY-AWS.md).

## 8. Roadmap recomendado
1. Backend remoto Terraform por ambiente y bloqueo de estado.
2. Despliegue ECS/ALB/HTTPS y conexion a RDS/S3/Secrets Manager.
3. Observabilidad administrada y control de costos.

## 9. Referencias complementarias
- Overview del repo: [README](../../README.md).
- Diagramas C4: [C4-CONTAINERS.svg](../01-architecture/C4-CONTAINERS.svg).
- Documento inicial del proyecto: [Documento base PDF](../05-general-docs/Proyecto_PQR_Documento_Inicial_v_0010.pdf).

---

Usa esta guía como índice maestro. Para cada etapa, abre el documento referenciado y ejecuta en el orden indicado.
