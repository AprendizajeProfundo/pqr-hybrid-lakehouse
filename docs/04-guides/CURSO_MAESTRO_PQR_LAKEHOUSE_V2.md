# Curso Maestro PQR Hybrid Lakehouse V2

Manual académico integral para estudiar, operar y migrar el proyecto **PQR Hybrid Lakehouse** desde cero (local) hasta una base real en AWS (Fase 1), con ruta de continuación a fases productivas.

Este documento **amplía** el curso maestro existente, incorpora el contexto completo del documento inicial del proyecto y organiza todas las guías disponibles en una secuencia didáctica.

---

## 0) Propósito del curso

Este curso existe para que cualquier estudiante o profesional pueda:

1. Entender el problema de negocio y su traducción técnica.
2. Levantar el entorno local completo sin atajos.
3. Ejecutar el pipeline Lakehouse por capas (Raw/Bronze/Silver/Gold).
4. Consumir analítica en dashboards y SQL.
5. Migrar la base de infraestructura a AWS con Terraform.
6. Validar técnicamente y operativamente que la base cloud quedó bien.
7. Continuar con un roadmap ordenado hacia operación real.

---

## 1) Contexto base del problema (fuente académica original)

El caso parte del documento inicial del curso, que define:

- Escenario institucional multicanal de PQRS.
- Volumen estimado (promedio y picos).
- Canales de entrada heterogéneos.
- Riesgos de trazabilidad y cumplimiento.
- Objetivo de PoC reproducible y auditable.
- SLA objetivo por tipo (P/Q/R/S).
- Ciclo de vida operativo del ticket y KPIs esperados.
- Justificación de arquitectura tipo Lakehouse.

Referencias fuente:

- [Proyecto_PQR_Documento_Inicial_v_0010.odt](../05-general-docs/Proyecto_PQR_Documento_Inicial_v_0010.odt)
- [Proyecto_PQR_Documento_Inicial_v_0010.pdf](../05-general-docs/Proyecto_PQR_Documento_Inicial_v_0010.pdf)
- [Estructura-repositorio-V0010.odt](../05-general-docs/Estructura-repositorio-V0010.odt)
- [Estructura-repositorio-V0010.pdf](../05-general-docs/Estructura-repositorio-V0010.pdf)

---

## 2) Ruta de aprendizaje recomendada (de cero a nube)

1. Fundamentos del proyecto y diseño.
2. Infraestructura local y operación de servicios.
3. Simulación y generación de datos PQRS.
4. ETL por capas y orquestación.
5. Consumo analítico (Streamlit/Metabase/SQL).
6. Seguridad y secretos.
7. Migración a AWS (principiantes + Terraform baseline).
8. Validación formal pre-nube y bitácora real de ejecución.
9. Plan de continuidad (Fase 2 y 3).

---

## 3) Índice maestro de guías (completo y enlazado)

### A. Guías troncales del curso

- [CURSO_MAESTRO_PQR_LAKEHOUSE.md](./CURSO_MAESTRO_PQR_LAKEHOUSE.md)
  - Base pedagógica original del curso maestro.
- [GUIDE-PQR-HYBRID-LAKEHOUSE.md](./GUIDE-PQR-HYBRID-LAKEHOUSE.md)
  - Guía general del proyecto como mapa integral de estudio.
- [CLASE_LOCAL2AWS_ALL.md](./CLASE_LOCAL2AWS_ALL.md)
  - Clase formal end-to-end, desde local hasta verificación en AWS.

### B. Diseño, arquitectura y fundamentos

- [GUIA-DISEÑO-e-INFRA.md](./GUIA-DISEÑO-e-INFRA.md)
  - Visión de diseño técnico e infraestructura por planos.
- [GUIDE-Gold-Schemas-SLA-SLO-Explicacion-Profunda.md](./GUIDE-Gold-Schemas-SLA-SLO-Explicacion-Profunda.md)
  - Modelado Gold, métricas SLA/SLO y lectura analítica.
- [GUIDE-Esquemas-Gold-SLA-SLO-Explicacion-Profunda-FUENTE-06SPEC.md](./GUIDE-Esquemas-Gold-SLA-SLO-Explicacion-Profunda-FUENTE-06SPEC.md)
  - Copia de respaldo de guía técnica ubicada originalmente en `docs/06-spec`.
- [GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md](./GUIDE-Init-Postgres-SQL-Explicacion-Detallada.md)
  - Esquema inicial SQL, propósito de tablas y relaciones.
- [GUIDE-Docker-Compose-YML-Explicacion-Paso-a-Paso.md](./GUIDE-Docker-Compose-YML-Explicacion-Paso-a-Paso.md)
  - Desglose pedagógico del `docker-compose.yml`.

### C. Infra local y operación de servicios

- [GUIDE-Implementacion-Infra-Local-Docker.md](./GUIDE-Implementacion-Infra-Local-Docker.md)
  - Implementación local con contenedores y dependencias mínimas.
- [GUIA-INFRA-LOCAL-DOCKER-FUENTE-INFRA.md](./GUIA-INFRA-LOCAL-DOCKER-FUENTE-INFRA.md)
  - Copia de respaldo de guía ubicada originalmente en `infra/docker`.
- [GUIDE-LEVANTANDO-SERVICIOS.md](./GUIDE-LEVANTANDO-SERVICIOS.md)
  - Encendido de stack local y validaciones iniciales.
- [GUIDE-BAJAR-SUBIR-STACK.md](./GUIDE-BAJAR-SUBIR-STACK.md)
  - Procedimientos limpios de apagado/arranque de stack.
- [GUIDE-OPERACION-LOCAL-COMANDOS.md](./GUIDE-OPERACION-LOCAL-COMANDOS.md)
  - Recetario operativo de comandos locales frecuentes.
- [GUIDE-ACCESO-UIS-LOCAL.md](./GUIDE-ACCESO-UIS-LOCAL.md)
  - Acceso a interfaces web locales (servicios y puertos).

### D. Simulación y generación de datos

- [GUIDE-GENERACION-SIMULACION-PQRS.md](./GUIDE-GENERACION-SIMULACION-PQRS.md)
  - Construcción de datasets simulados de eventos PQRS.
- [GUIDE-ESTUDIANTES-SIMULADOR-PASO-A-PASO.md](./GUIDE-ESTUDIANTES-SIMULADOR-PASO-A-PASO.md)
  - Versión didáctica detallada para estudiantes.
- [GUIDE-AJUSTE-SIMULADOR-PDF-2026.md](./GUIDE-AJUSTE-SIMULADOR-PDF-2026.md)
  - Ajustes finos del simulador y consistencia de outputs.

### E. ETL y orquestación

- [GUIDE-ETL-DESDE-JSONL-A-PLATAFORMA.md](./GUIDE-ETL-DESDE-JSONL-A-PLATAFORMA.md)
  - Flujo completo desde eventos JSONL hasta capas analíticas.
- [GUIDE-ETL-POR-ETAPAS-Y-ORQUESTACION-PREFECT.md](./GUIDE-ETL-POR-ETAPAS-Y-ORQUESTACION-PREFECT.md)
  - Ejecución por etapas y control con Prefect.
- [GUIDE-COMANDOS-ETL-RAPIDO.md](./GUIDE-COMANDOS-ETL-RAPIDO.md)
  - Atajos de ejecución ETL para iteración rápida.

### F. Analítica y consumo

- [GUIDE-DASHBOARD-Y-APP-ANALITICA-PQRS.md](./GUIDE-DASHBOARD-Y-APP-ANALITICA-PQRS.md)
  - Explotación analítica en aplicación y tableros.
- [GUIDE-PLAN-ANALITICA-KPI-Y-MAPAS-PQRS.md](./GUIDE-PLAN-ANALITICA-KPI-Y-MAPAS-PQRS.md)
  - Plan de KPIs, vistas de negocio y análisis geográfico.
- [GUIDE-METABASE-DASHBOARD-EJECUTIVO-PQRS.md](./GUIDE-METABASE-DASHBOARD-EJECUTIVO-PQRS.md)
  - Diseño y consultas SQL para dashboard ejecutivo en Metabase.

### G. Seguridad y gobierno técnico

- [GUIDE-SEGURIDAD-SECRETS.md](./GUIDE-SEGURIDAD-SECRETS.md)
  - Gestión de secretos, prácticas de seguridad y límites operativos.

### H. Migración a AWS y Terraform

- [GUIDE-MIGRATION-LOCAL-TO-CLOUD.md](./GUIDE-MIGRATION-LOCAL-TO-CLOUD.md)
  - Estrategia general de migración de entorno local a nube.
- [GUIDE-MIGRACION-AWS-PRINCIPIANTES.md](./GUIDE-MIGRACION-AWS-PRINCIPIANTES.md)
  - Ruta para primera migración con perfil principiante.
- [GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md](./GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md)
  - Baseline IaC, validaciones y roadmap de evolución.
- [GUIDE-DEPLOY-AWS.md](./GUIDE-DEPLOY-AWS.md)
  - Flujo concreto de despliegue y verificación en AWS.

### I. Validación formal y bitácora de ejecución

- [TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md](./TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md)
  - Plantilla formal para checklist y aprobación técnica.
- [ACTA-VALIDACION-PRE-NUBE-2026-03-06.md](./ACTA-VALIDACION-PRE-NUBE-2026-03-06.md)
  - Acta ejecutada del proyecto para habilitar paso a nube.
- [BITACORA-MIGRACION-AWS-FASE1.md](./BITACORA-MIGRACION-AWS-FASE1.md)
  - Registro cronológico real de decisiones, errores, correcciones y resultados.

### J. Clase corta y apoyo docente

- [GUIDE-CLASE-4HORAS-LAKEHOUSE.md](./GUIDE-CLASE-4HORAS-LAKEHOUSE.md)
  - Versión compacta para clase intensiva de 4 horas.

---

## 4) Ciclo completo del proyecto (visión profesional)

### Etapa 1: Comprender el problema

Se inicia con el documento académico base para fijar vocabulario, objetivos y criterios de éxito:

- Multicanalidad.
- Trazabilidad completa del ticket.
- SLA por tipo PQRS.
- KPIs de operación y cumplimiento.

### Etapa 2: Preparar entorno local reproducible

Se construye una base confiable en máquina local:

- Entorno Python gestionado.
- Servicios con Docker Compose.
- Variables de entorno y secretos separados de código.

### Etapa 3: Simular datos de manera controlada

Se generan eventos sintéticos con realismo operacional y reproducibilidad para pruebas comparables entre corridas.

### Etapa 4: Transformar datos por arquitectura Medallón

Se procesa el flujo Raw/Bronze/Silver/Gold con enfoque de calidad, trazabilidad y consumo analítico.

### Etapa 5: Exponer valor analítico

Se publican métricas, tableros y consultas orientadas a toma de decisiones (operación, SLA y backlog).

### Etapa 6: Migrar infraestructura base a AWS con IaC

Se ejecuta Terraform en modo controlado (`init`, `plan`, `apply`) y se valida creación de red, buckets, ECR, ECS y secretos.

### Etapa 7: Verificar, documentar y auditar

Se registra evidencia en actas y bitácora, dejando trazabilidad pedagógica y operativa para nuevas cohortes.

### Etapa 8: Continuidad

Se planifican siguientes fases: despliegue de cargas (ECS/Fargate), datos administrados (RDS), exposición segura (ALB+HTTPS), observabilidad y costos.

---

## 5) Roadmap consolidado (después de Fase 1)

1. Publicar imágenes Docker en ECR (`streamlit`, `prefect`, `metabase`, `dask`).
2. Definir Task Definitions y Services en ECS/Fargate.
3. Provisionar RDS PostgreSQL y migrar capa serving/control.
4. Conectar secretos de producción desde Secrets Manager.
5. Habilitar balanceador (ALB), dominio y TLS.
6. Activar observabilidad y alarmas de costo/uso.
7. Ejecutar pruebas E2E y actualizar documentación final de operación.

---

## 6) Criterio de “listo para enseñar / listo para operar”

El proyecto se considera listo para formación y avance cloud cuando:

- Guías están completas, consistentes y enlazadas.
- Pipeline local corre de extremo a extremo.
- Dashboards consumen datos Gold correctamente.
- Terraform plan/apply reproducen infraestructura objetivo.
- Existen acta y bitácora con evidencia verificable.
- Hay roadmap explícito de siguientes fases.

---

## 7) Nota de curaduría documental

Para asegurar que no quedaran guías aisladas fuera del catálogo principal, se incorporaron copias de referencia dentro de `docs/04-guides`:

- `GUIDE-Esquemas-Gold-SLA-SLO-Explicacion-Profunda-FUENTE-06SPEC.md`
- `GUIA-INFRA-LOCAL-DOCKER-FUENTE-INFRA.md`

Esto deja una biblioteca de estudio centralizada para estudiantes y equipos técnicos.

---

## 8) Sugerencia de uso docente

Para una cohorte nueva, usar este orden:

1. Documento inicial del caso (`docs/05-general-docs`).
2. Curso maestro base + este V2.
3. Infra local + simulación + ETL.
4. Dashboards y lectura KPI/SLA.
5. Migración AWS principiantes + Terraform baseline.
6. Acta + bitácora como cierre evaluable.

Con esto, el estudiante recorre todo el ciclo: **problema -> datos -> arquitectura -> operación -> nube -> evidencia**.
