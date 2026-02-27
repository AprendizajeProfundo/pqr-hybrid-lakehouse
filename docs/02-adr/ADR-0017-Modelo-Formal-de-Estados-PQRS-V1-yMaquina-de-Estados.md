# ADR-0017 — Modelo Formal de Estados PQRS (V1) y Máquina de Estados

**Estado:** FINAL  
**Fecha:** 2026-02-25  
**Sistema/Proyecto:** PQR Hybrid Lakehouse (PoC)  
**Decisores:** Arquitectura + Data Engineering  
**Relacionado:** ADR-0016 (Base de Seguimiento PQRS + Lakehouse en RustFS/S3)

---

## 1. Contexto

El PoC requiere **seguimiento (tracking)** completo y auditable del ciclo de vida de cada PQRS, para habilitar:

- métricas operativas (volumen, backlog, tiempos),
- métricas de cumplimiento (SLA, vencidas, retrasos),
- análisis estadístico (distribuciones, series, flujos),
- reproducibilidad (runs deterministas, auditoría),
- compatibilidad futura con un **sistema transaccional de gestión**, sin implementarlo en este MVP.

Para ello, es necesario fijar un **modelo formal de estados** y una **máquina de estados** (transiciones permitidas), explícitos y gobernados.

---

## 2. Decisión

Se adopta el **Modelo Formal de Estados PQRS (V1)** como estándar del PoC, con:

1) **Catálogo de estados** gobernado en BD (`dim_status`)  
2) **Catálogo de transiciones permitidas** (`dim_status_transition`)  
3) **Semántica de SLA por estado** (`sla_behavior`)  
4) **Fuente versionada** en repo: `configs/pqrs_status_v1.yaml`  
5) **Validación obligatoria** en el pipeline Silver (rechazo/flag de transiciones no permitidas)  

Este modelo es canónico para:
- simulación sintética,
- ingestión real futura,
- cálculo de métricas,
- auditoría.

---

## 3. Estados Canónicos (V1)

Estados oficiales:

- RECEIVED
- RADICATED
- CLASSIFIED
- ASSIGNED
- IN_PROGRESS
- ON_HOLD
- RESPONDED
- CLOSED
- ARCHIVED
- REOPENED

Semántica:

- `is_terminal`: indica fin del ciclo.
- `sla_behavior`: define comportamiento del reloj SLA:
  - `NONE`: no corre SLA
  - `START`: inicia SLA
  - `RUN`: corre SLA
  - `PAUSE`: pausa SLA
  - `STOP`: detiene SLA

---

## 4. Máquina de estados: transiciones permitidas (V1)

Solo se permiten estas transiciones:

- RECEIVED → RADICATED
- RADICATED → CLASSIFIED
- CLASSIFIED → ASSIGNED
- ASSIGNED → IN_PROGRESS
- IN_PROGRESS → RESPONDED
- IN_PROGRESS → ON_HOLD
- ON_HOLD → IN_PROGRESS
- RESPONDED → CLOSED
- CLOSED → ARCHIVED
- CLOSED → REOPENED
- REOPENED → IN_PROGRESS

Cualquier otra transición es:
- **Error de calidad** (si viene de simulación o pipeline)
- **Incidente de datos** (si viene de un futuro sistema real)

---

## 5. Reglas de SLA (V1)

- El SLA **inicia** en `RADICATED` (`START`)
- El SLA **corre** en: `CLASSIFIED`, `ASSIGNED`, `IN_PROGRESS`, `RESPONDED`, `REOPENED` (`RUN`)
- El SLA **se pausa** en `ON_HOLD` (`PAUSE`)
- El SLA **se detiene** en `CLOSED` (`STOP`)
- `RECEIVED` y `ARCHIVED` no aportan tiempo SLA (`NONE`)

---

## 6. Alternativas consideradas

1) **Estados “libres” como texto sin catálogo**  
   - Rechazada: imposibilita validación, métricas consistentes y auditoría.
2) **Estados hardcodeados en código**  
   - Rechazada: baja gobernanza, difícil evolución, riesgo en despliegue.
3) **Workflow completo tipo BPMN**  
   - Rechazada para MVP: sobre-ingeniería; el PoC requiere tracking analítico, no motor de procesos.

---

## 7. Consecuencias

### Positivas
- Métricas y SLA calculables sin ambigüedad.
- Trazabilidad fuerte (eventos de transición).
- Validación automática de coherencia.
- Base preparada para implementación transaccional futura.

### Costos/Trade-offs
- Requiere disciplina: catálogo + transiciones + validación.
- Requiere bootstrap de dimensiones y control de versiones.

---

## 8. Criterios de aceptación (Definition of Done)

- Existe `configs/pqrs_status_v1.yaml` versionado.
- BD contiene `dim_status` y `dim_status_transition` pobladas con V1.
- Pipeline Silver valida que cada transición observada está permitida.
- Todo ticket simulado:
  - inicia con RECEIVED
  - tiene al menos una transición a RADICATED
  - termina en CLOSED o ARCHIVED (conforme reglas)
- Cálculo SLA respeta `sla_behavior`.

---

## 9. Implementación (artefactos vinculantes)

- `docs/spec/SPEC-0017-pqrs-states-v1.md`
- `configs/pqrs_status_v1.yaml`
- `sql/bootstrap/0017_dim_status_seed.sql` (opcional, recomendado)

---