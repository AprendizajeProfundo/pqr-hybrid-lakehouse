# SPEC-0018 — Clasificación PQRS (V1 + Evolución)

**Versión:** 1.0  
**Fecha:** 2026-02-25  
**Deriva de:** ADR-0018  

---

# 1. OBJETIVO

Definir:

- Esquema de datos de clasificación
- Contrato técnico
- Fase 1 (Rules)
- Fase 2 (ML clásico)
- Fase 3 (Embeddings)
- Métricas de evaluación
- Integración con Lakehouse

---

# 2. MODELO DE DATOS

## 2.1 Tabla Silver

```sql
CREATE TABLE IF NOT EXISTS silver_preclassification (
  ticket_id UUID NOT NULL,
  run_id UUID NOT NULL,
  model_type VARCHAR(30) NOT NULL,       -- rules / tfidf_lr / embeddings
  model_version VARCHAR(50) NOT NULL,
  predicted_type VARCHAR(1) NOT NULL,    -- P/Q/R/S
  predicted_priority VARCHAR(10) NOT NULL, -- alta/media/baja
  score NUMERIC(5,4) NOT NULL,
  explain_json JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (ticket_id, run_id, model_version)
);
``` 

## 2.2 Tabla Gold (Métricas Agregadas)

```sql
CREATE TABLE IF NOT EXISTS gold_pqrs_metrics (
  date DATE NOT NULL,
  type VARCHAR(1) NOT NULL,  -- P/Q/R/S
  priority VARCHAR(10) NOT NULL, -- alta/media/baja
  count INTEGER NOT NULL,
  avg_score NUMERIC(5,4),
  run_id UUID NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (date, type, priority, run_id)
);
```
## 3.1 Entrada

+ subject
+ body

## 3.2 Proceso

1. Normalización:

    + lowercase
    + quitar tildes
    + eliminar caracteres especiales

2. Tokenización simple
3. Matching contra diccionario
4. Puntaje por frecuencia
5. Selección por máximo puntaje
6. score = max_score / total_score

## 3.3 Fuente de reglas

Archivo:

```text
docs/07-config/pqrs_preclass_rules_v1.yaml
```

# 4. FASE 2 — MODELO SUPERVISADO CLÁSICO
## 4.1 Datos de entrenamiento

+ Ground truth generado por simulador:
+ true_type
+ true_priority

## 4.2 Pipeline

1. Vectorización TF-IDF
2. Logistic Regression
3. Validación (train/test split)
    + Métricas:
    + Accuracy
    + Precision
    + Recall
    + F1
    + Confusion matrix

## 4.3 Registro de modelo

Guardar en:

```text
models/tfidf_lr_v1.pkl
```

metadata en 

```text
meta.model_registry (opcional)
```

# 5. FASE 3 — EMBEDDINGS (OPCIONAL AVANZADO)
## 5.1 Pipeline

    + Generar embeddings
    + Clasificador lineal
    + Guardar versión
    + Evaluar

No obligatorio para MVP.

# 6. MÉTRICAS DE EVALUACIÓN

Registrar en:

```text
meta.model_evaluation
```

```sql
CREATE TABLE IF NOT EXISTS meta_model_evaluation (
  model_version VARCHAR(50),
  run_id UUID,
  accuracy NUMERIC(5,4),
  f1 NUMERIC(5,4),
  created_at TIMESTAMP DEFAULT NOW()
);
```

# 7. INTEGRACIÓN CON LAKEHOUSE

Secuencia:

```text
Raw → Bronze → Silver_messages → Preclassification → Silver_preclassification → Gold_metrics
````

# 8. VERSIONADO

Cada clasificación debe registrar:

    + model_type
    + model_version
    + run_id

Nunca sobrescribir histórico.

# 9. PRUEBAS MÍNIMAS

   + Clasificar 100 tickets
   + Verificar cobertura 100%
   + Verificar distribución razonable
   + Verificar score ∈ [0,1]
   + Comparar rules vs tfidf_lr

10. CRITERIO DE ACEPTACIÓN

    + silver_preclassification poblada
    + Métricas evaluadas
    + Modelo versionado
    + Reproducibilidad garantizada
