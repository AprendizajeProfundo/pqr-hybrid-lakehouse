# ADR-0018 — Modelo Formal de Clasificación PQRS

**Estado:** FINAL  
**Fecha:** 2026-02-25  
**Sistema:** PQR Hybrid Lakehouse  
**Relacionado:** ADR-0010 (Tracking), ADR-0017 (Estados)

---

# 1. Contexto

La clasificación de PQRS es crítica para:

- Segmentación estadística
- Métricas por tipo
- SLA diferenciado
- Backlog por categoría
- Análisis geográfico
- Modelos predictivos posteriores

Se requiere:

- Una solución mínima inmediata (determinista)
- Un camino formal hacia ML supervisado
- Reproducibilidad total por run
- Versionado de modelos/reglas

---

# 2. Decisión

Se adopta un modelo de clasificación en **fases evolutivas controladas**:

## Fase 1 — Baseline Determinista (Rules Engine)
- Clasificación por reglas y diccionario
- 100% reproducible
- Explicable
- Integrado en Silver

## Fase 2 — Modelo Supervisado Clásico
- TF-IDF + Logistic Regression
- Entrenado con truth sintético
- Versionado y evaluado

## Fase 3 — Modelo Embeddings / Encoder
- Vectorización semántica
- Clasificador lineal o fine-tuning
- Opcional en PoC avanzado

Cada fase:

- Versionada
- Registrada en meta.etl_runs
- Asociada a run_id
- No reemplaza histórico anterior

---

# 3. Alcance

Incluye:

- Clasificación de tipo PQRS (P/Q/R/S)
- Clasificación de prioridad (alta/media/baja)
- Score
- Explicabilidad
- Versionado

Excluye:

- Deep Learning pesado
- Sistemas en línea
- Clasificación en tiempo real (este es batch)

---

# 4. Consecuencias

✔ Analítica inmediata  
✔ Evolución natural  
✔ Comparación de modelos  
✔ Control de drift  
✔ Métricas de desempeño  

---

# 5. Criterios de aceptación

- Existe tabla silver_preclassification
- Cada ticket con texto tiene clasificación
- Se guarda model_version o rules_version
- Se puede comparar rendimiento entre versiones
- Se puede recalcular sin alterar histórico