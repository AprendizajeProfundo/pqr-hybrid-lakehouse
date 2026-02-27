# DATA-LAYOUT-S3.md

## 1. Objetivo

Este documento define formalmente la organización del Data Lake del proyecto pqr-hybrid-lakehouse sobre almacenamiento tipo S3 (AWS S3, RustFS u otro compatible).

Objetivos:

- Garantizar orden estructural y escalabilidad.
- Asegurar trazabilidad y reproducibilidad.
- Establecer reglas claras de gobernanza.
- Definir políticas de inmutabilidad y seguridad.

---

## 2. Principios de diseño

1. S3 es almacenamiento objeto, no un filesystem.
2. Los prefijos (keys) determinan rendimiento, gobernanza y costo.
3. La capa **Raw** es **append-only** (inmutable).
4. Las capas **Bronze / Silver / Gold** son **regenerables** (derivadas).
5. Nunca se sobrescribe histórico en producción.
6. El layout es una decisión arquitectónica (no “carpetas”), y debe ser consistente en todos los pipelines.

---

## 3. Estructura de buckets

### 3.1 Opción recomendada (proyecto académico / PoC)

Un único bucket principal:

- `s3://pqr-hybrid-lakehouse-datalake/`

Separación por capas mediante prefijos:

- `raw/`
- `bronze/`
- `silver/`
- `gold/`
- `tmp/`
- `logs/`

---

### 3.2 Alternativa enterprise (producción con gobernanza estricta)

Buckets por capa:

- `pqr-hybrid-lakehouse-raw-{env}`
- `pqr-hybrid-lakehouse-bronze-{env}`
- `pqr-hybrid-lakehouse-silver-{env}`
- `pqr-hybrid-lakehouse-gold-{env}`

> Para el proyecto actual se adopta **bucket único** + prefijos por simplicidad operacional.

---

## 4. Prefijos, particionado y formatos

### 4.1 RAW (append-only, inmutable)

Formato recomendado:

- `raw/{fuente}/{year}/{month}/{day}/`

Ejemplos:

- `raw/web/2026/02/17/ingest_001.json`
- `raw/callcenter/2026/02/17/audio_023.wav`
- `raw/whatsapp/2026/02/17/chat_00019.json`

#### Justificación del particionado por fecha

- Permite lectura selectiva y reduce scans.
- Facilita reglas de retención (lifecycle).
- Soporta reconstrucción por día (reproducibilidad).
- Compatible con motores tipo Athena/Spark/Dask (por predicados de partición).

**Antipatrón** (evitar):

- `raw/archivo.json`

---

### 4.2 BRONZE (normalizado, aún granular)

Formato:

- `bronze/{dataset}/{year}/{month}/{day}/`

Ejemplo:

- `bronze/pqr-hybrid-lakehouse_events/2026/02/17/part-0001.parquet`

Formato recomendado:

- **Parquet**
- Compresión **Snappy** (o ZSTD si tu stack la soporta consistentemente)

---

### 4.3 SILVER (modelo limpio estructurado)

Formato:

- `silver/{tabla}/{year}/{month}/`

Ejemplo:

- `silver/pqr-hybrid-lakehouse_structured/2026/02/part-0001.parquet`

En Silver ya existe:

- tipado correcto
- validaciones aplicadas
- normalización mínima
- enriquecimiento (por ejemplo, geocodificación, catálogos)

---

### 4.4 GOLD (analítica y consumo)

Formato:

- `gold/{producto_analitico}/`

Ejemplos:

- `gold/dashboard_metrics/monthly_summary.parquet`
- `gold/kpi/top_categories.parquet`

Gold no requiere partición diaria si son agregados.

---

## 5. Convenciones de nombres

### 5.1 Buckets

Reglas:

- solo minúsculas
- sin espacios
- sin underscores
- sin caracteres especiales

Correcto:

- `pqr-hybrid-lakehouse-datalake`
- `pqr-hybrid-lakehouse-raw-prod`

Incorrecto:

- `pqr-hybrid-lakehouse_DataLake`
- `pqr-hybrid-lakehouse_data_lake`

---

### 5.2 Prefijos

Reglas:

- `snake_case`
- sin espacios
- sin mayúsculas

Correcto:

- `pqr-hybrid-lakehouse_events`
- `call_center_audio`
- `structured_output`

---

### 5.3 Archivos

Formato recomendado:

- `{dataset}_{timestamp}_{uuid}.ext`

Ejemplo:

- `pqr-hybrid-lakehouse_20260217T102300Z_9fa8.parquet`

Evitar:

- `data_final_v2_new.parquet`
- `ok_final_ahora_si.parquet`

---

## 6. Política de inmutabilidad

### 6.1 RAW = append-only

Reglas estrictas:

- no se sobrescribe
- no se elimina manualmente
- solo se agregan objetos nuevos
- correcciones se realizan en capas superiores (Bronze/Silver/Gold)

Motivo:

Raw es evidencia histórica y base de auditoría (trazabilidad + reproducibilidad).

---

### 6.2 Manejo de datos inválidos/corruptos

Nunca borrar “a mano”. Opciones:

1) Marcar por nombre:

- `raw/web/2026/02/17/file.json.invalid`

2) Marcar con metadata (si tu backend lo soporta de forma consistente):

- `x-data-status=invalid`
- `x-invalid-reason=...`

3) Registrar en `logs/`:

- `logs/data_quality/2026/02/17/invalid_objects.json`

---

## 7. Estrategia de evolución de esquema

Nunca sobrescribir histórico cuando cambia el modelo.

Opciones:

### 7.1 Versionado por prefijo

- `silver/pqr-hybrid-lakehouse_structured/v1/`
- `silver/pqr-hybrid-lakehouse_structured/v2/`

### 7.2 Versionado por partición

- `silver/pqr-hybrid-lakehouse_structured/schema_version=2/`

Esto permite coexistencia de modelos y migraciones progresivas.

---

## 8. Lifecycle y retención

Recomendación general:

- **Raw**: retención extendida (1–3 años o lo que defina la entidad).
- **Bronze/Silver**: regenerables → retención menor.
- **Gold**: depende de consumo analítico y auditoría.

Regla:

> Si no puedes regenerarlo, es crítico → debe ser inmutable y con retención fuerte.

---

# 9. Seguridad (IAM + policies)

## 9.1 Principio base

Aplicar **Least Privilege**:

- cada rol tiene solo lo necesario
- deny explícitos para acciones de alto riesgo en Raw
- segmentación por prefijos (keys)

---

## 9.2 Roles recomendados (modelo lógico)

### A) Rol de Ingesta

Permisos:

- `PutObject` en `raw/*`
- sin `DeleteObject`
- sin escritura en silver/gold

Concepto:

- Allow: `s3:PutObject` en `.../raw/*`
- Deny: `s3:DeleteObject` en `.../raw/*`

---

### B) Rol de Procesamiento

Permisos:

- Read: `raw/*`
- Write: `bronze/*`, `silver/*`
- Deny: delete en `raw/*`

---

### C) Rol Analítico

Permisos:

- Read: `silver/*`, `gold/*`
- Deny: write en todas las capas (solo lectura)

---

### D) Rol Administrador

Permisos completos (uso restringido, auditado).

---

## 9.3 Ejemplos de políticas (AWS IAM JSON)

> Ajusta `arn:aws:s3:::pqr-hybrid-lakehouse-datalake` al nombre real del bucket.

### 9.3.1 Deny borrar objetos en Raw (protección fuerte)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDeleteOnRaw",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteObjectVersion"
      ],
      "Resource": "arn:aws:s3:::pqr-hybrid-lakehouse-datalake/raw/*"
    }
  ]
}