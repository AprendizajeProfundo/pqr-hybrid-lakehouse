# 📖 Explicación Profunda: Sección 4. Esquemas Postgres

---

## ¿Por qué Silver es desnormalizado y Bronze/Gold no?

La respuesta está en el **propósito de cada capa del lakehouse**.

### 🔵 Bronze: Tabla Única para Raw normalizado

```sql
bronze_pqrs_events (
  event_id, ticket_id, source_channel, event_type, ts, data JSONB
)
```

- Bronze recibe datos **tal como vienen del Raw**, pero tipados.
- Es un depósito de eventos sin transformación lógica.
- **Una sola tabla** porque los eventos son eventos: cada fila es un acontecimiento aislado.
- No necesita relaciones: es un historiador de ocurrencias.
- La estructura es **ligera y directa**: eventos → Parquet → Postgres.

### 🟢 Silver: Múltiples tablas desnormalizadas

```sql
silver_tickets       -- dimensión principal
silver_messages      -- hechos asociados a tickets
silver_status_events -- histórico de cambios de estado
```

- Silver **curada y enriquecida** los datos para análisis.
- Aquí es donde **transformamos eventos en entidades de negocio**.

**¿Por qué desnormalizamos?**

Un evento raw `STATUS_CHANGED` es:
```json
{
  "event_type": "STATUS_CHANGED",
  "ticket_id": "abc-123",
  "ts": "2026-02-25T10:00:00Z",
  "data": {
    "from": "RECEIVED",
    "to": "RADICATED",
    "actor": "agent"
  }
}
```

Pero el **negocio pregunta cosas como:**
- "¿Cuántos tickets abré hoy?" → tablas separadas por tipo de evento
- "¿Quién respondió a este ticket?" → historial en `silver_messages`
- "¿En qué estado está ahora?" → `silver_tickets.current_status`

**Solución: desnormalizar en tablas específicas por dominio:**

| Tabla | Rol | Ejemplo |
|-------|-----|---------|
| `silver_tickets` | Foto actual de cada ticket | ticket_id, current_status, sla_due_at |
| `silver_messages` | Línea temporal de respuestas | message_id, ticket_id, role, text, ts |
| `silver_status_events` | Trazabilidad de cambios | event_id, status_from, status_to, ts |

Así un analista **no tiene que descomponer JSON** ni hacer JOINs complejos de eventos.

### 🟡 Gold: Agregadas por caso de uso

```sql
gold_kpi_volume_daily     -- recuentos por canal y tipo
gold_kpi_backlog_daily    -- pendientes por región
gold_kpi_sla_daily        -- métricas de cumplimiento
```

- Gold es el **formato listo para Dashboard/Ejecutivos**.
- Una tabla **por KPI**, no por entidad de datos.
- Ya calculadas, desnormalizadas, listas para graficar.
- Nadie hace requerimientos o JOINs; es "copy-pasta" directo al BI.

> **Patrón:** Bronze = datos brutos tipados | Silver = tablas curadas | Gold = métricas finales

---

## 📊 Detalle profundo de las tablas Gold

### 1. `gold_kpi_volume_daily`

```sql
CREATE TABLE gold_kpi_volume_daily (
  day DATE,
  channel VARCHAR(20),        -- 'email', 'webform', 'chat', 'call'
  pqrs_type VARCHAR(1),       -- 'P', 'Q', 'R', 'S'
  tickets_count INTEGER,
  PRIMARY KEY (day, channel, pqrs_type)
);
```

**¿Qué mide?**
- El **volumen de tickets ingresados** por día, canal y tipo PQRS.

**Ejemplo de datos:**

| day | channel | pqrs_type | tickets_count |
|-----|---------|-----------|---------------|
| 2026-02-25 | email | P | 25 |
| 2026-02-25 | email | Q | 18 |
| 2026-02-25 | webform | P | 12 |
| 2026-02-25 | chat | R | 8 |
| 2026-02-26 | email | P | 30 |

**Interpretación:**
- El 25 de febrero ingresaron 25 PQR ("Peticiones") por email.
- El 25 ingresaron 18 "Quejas" por email.
- En total, el volumen diario refleja la carga de trabajo.

**Uso en Dashboard:**
```
Gráfico: líneas o barras apiladas por canal.
Eje X: días
Eje Y: cantidad de tickets
Colores: canal (azul=email, verde=webform, etc.)
```

---

### 2. `gold_kpi_backlog_daily`

```sql
CREATE TABLE gold_kpi_backlog_daily (
  day DATE,
  pqrs_type VARCHAR(1),
  region VARCHAR(50),          -- 'Bogotá', 'Cali', 'Medellín', etc. (valor tomado de la dimensión `dim_geo` que contiene códigos DANE y geometría para mapas)
  backlog_count INTEGER,
  PRIMARY KEY (day, pqrs_type, region)
);
```

**¿Qué mide?**
- El número de tickets **abiertos/pendientes** al final del día, por tipo y región. La región se deriva de `dim_geo`, que ahora incorpora códigos DANE y coordenadas para análisis espacial.

**El concepto de BACKLOG:**

> **Backlog** = tickets que llevan tiempo abiertos y aún no se han cerrado.

Imagine una cola en un supermercado:
- Diariamente entran tickets nuevos (volumen).
- Diariamente se cierran tickets (resoluciones).
- El **backlog** es lo que queda en espera: la "cola" acumulada.

Si el backlog crece significa:
- Lluvia: demasiados tickets nuevos.
- Sequía: muy pocas resoluciones/personal insuficiente.

**Ejemplo de datos:**

| day | pqrs_type | region | backlog_count |
|-----|-----------|--------|---------------|
| 2026-02-25 | P | Bogotá | 45 |
| 2026-02-25 | P | Cali | 12 |
| 2026-02-25 | Q | Bogotá | 8 |
| 2026-02-26 | P | Bogotá | 52 |

**Interpretación:**
- El 25/02 había 45 Peticiones pendientes en Bogotá.
- El 26/02 aumentó a 52 (probablemente ingresaron más que lo que se cerró).

**En Dashboard:**
```
Mapa de calor por región y tipo PQRS.
Alerta: si backlog > umbral (p.ej., > 100) → rojo.
```

---

### 3. `gold_kpi_sla_daily`

```sql
CREATE TABLE gold_kpi_sla_daily (
  day DATE,
  pqrs_type VARCHAR(1),
  within_sla_pct NUMERIC(5,2),  -- porcentaje: 0.00 a 100.00
  overdue_count INTEGER,        -- cuántos incumplieron
  avg_overdue_days NUMERIC(5,2),-- días en promedio de retraso
  PRIMARY KEY (day, pqrs_type)
);
```

**¿Qué mide?**
- El cumplimiento de **promesas de tiempo** (SLA) diarias.

**Ejemplo de datos:**

| day | pqrs_type | within_sla_pct | overdue_count | avg_overdue_days |
|-----|-----------|----------------|---------------|------------------|
| 2026-02-25 | P | 92.50 | 3 | 1.2 |
| 2026-02-25 | Q | 88.00 | 2 | 2.5 |
| 2026-02-25 | R | 95.00 | 1 | 0.8 |
| 2026-02-26 | P | 90.00 | 5 | 1.8 |

**Interpretación:**
- El 25/02, el 92.5% de Peticiones se resolvieron dentro del plazo.
- El 7.5% (3 tickets) se salieron del SLA.
- Esos 3 tickets en promedio se demoraron 1.2 días más de lo prometido.

---

## ⏰ SLA vs SLO: Conceptos Críticos

### 🔴 SLA (Service Level Agreement)

**Definición:**
> Un **acuerdo contractual** entre proveedor y cliente sobre el nivel de servicio garantizado.
> Si no se cumple, hay penalidades.

**En contexto PQRS:**
- Promesa a ciudadanos: "Responderemos Peticiones en máximo **10 días hábiles**".
- Si un ticket Petición no se cierra en 10 días, es **incumplimiento de SLA**.

**Ejemplos reales en Colombia:**

| Tipo PQRS | SLA | Ley |
|-----------|-----|-----|
| Peticiones (P) | 10 días hábiles | Código de Procedimiento Administrativo Colombiano |
| Quejas (Q) | 30 días hábiles | Decreto 2649 |
| Reclamos (R) | 30 días hábiles | Decreto 2649 |
| Sugerencias (S) | 30 días para responder | Decreto 2649 |

### 🟢 SLO (Service Level Objective)

**Definición:**
> Un **objetivo interno** que se fija para asegurar el SLA.
> Es un "colchón" para no incumplir la ley.

**Ejemplo:**
- SLA legal = 10 días para Peticiones.
- SLO interno = 8 días para Peticiones.
  - Si fijamos 8, tenemos 2 días de margen antes de violar la ley.
  - Es más estricto que la promesa al ciudadano.

### 📊 Diferencia práctica en la tabla `gold_kpi_sla_daily`

```
Día X:
- SLA = máximo 10 días → 8 tickets Peticion cerrados de 8 en SLA = 100%
- SLO = máximo 8 días → de esos 8, solo 7 en SLO; 1 se fue a 9 días = 87.5%

Reporte al ejecutivo:
"Cumplimos SLA legal 100%, pero solo 87.5% de SLO interno."
→ Mensaje: "Estamos bien legalmente pero necesitamos mejorar proceso."
```

### 🧮 Cálculo en el pipeline Silver → Gold

```python
# Pseudocódigo en el pipeline

for ticket in fechados_hoy:
    dias_tomado = ticket.closed_at - ticket.created_at
    
    # Buscar SLA según tipo PQRS
    sla_dias = slas[ticket.pqrs_type]  # P→10, Q→30, etc.
    
    if dias_tomado <= sla_dias:
        within_sla = True
    else:
        within_sla = False
        overdue_dias = dias_tomado - sla_dias

# Agregado diario
total = count(tickets_today)
within = count(within_sla == True)
overdue_count = count(within_sla == False)
within_sla_pct = (within / total) * 100
avg_overdue = avg(overdue_dias for overdue)
```

---

## 🔗 Cómo Silver alimenta Gold

### Flujo de transformación

```
silver_tickets (foto de cada ticket hoy)
    ↓
Filtrar: closed_at es hoy
    ↓
Calcular: dias_en_sla = (closed_at - created_at) vs SLA
    ↓
Agrupar por: day, pqrs_type [, region si es backlog]
    ↓
Contar: within_sla_pct, overdue_count, avg_overdue_days
    ↓
gold_kpi_sla_daily ← insertar

silver_tickets (solo abiertos = closed_at IS NULL)
    ↓
Agrupar por: day, pqrs_type, region
    ↓
Contar: backlog_count
    ↓
gold_kpi_backlog_daily ← insertar

silver_tickets (todos creados hoy)
    ↓
Agrupar por: day, source_channel, pqrs_type
    ↓
Contar: tickets_count
    ↓
gold_kpi_volume_daily ← insertar
```

---

## 📌 Resumen: Tabla comparativa de capas

| Aspecto | Bronze | Silver | Gold |
|---------|--------|--------|------|
| **Estructura** | Una tabla de eventos | Varias tablas curadas | Tablas de KPI |
| **Formato** | JSON tipado (Parquet) | Relacional normalizado | Agregadas/Desnormalizadas |
| **Usuario** | Data engineer | Data analyst, BI developers | Ejecutivos, dashboards |
| **Consulta típica** | "Dame todos los eventos de X" | "¿Cuál es el estado actual de ticket Y?" | "¿Cuál fue el SLA el mes pasado?" |
| **Cambio de datos** | Inmutable (append-only) | Actualizable (SCD) | Regenerable cada noche |

---

## 🎓 Preguntas para tus estudiantes

1. Si mañana llegan 100 peticiones pero se cierran 50, ¿el backlog sube o baja?
   > **Sube en 50** (entran 100, salen 50 → +50 neto).

2. Un ticket se creó el lunes, se cerró el viernes (SLA P = 10 días) ¿en SLA?
   > **Sí**, 4 días < 10 días.

3. ¿Puede un backlog ser 0?
   > **Sí, si todos los tickets están cerrados.** Ideal pero raro.

4. ¿Por qué SLO es más estricto que SLA?
   > **Como margen de seguridad.** Si SLA = 10 y SLO = 8, tienes 2 días antes de perder dinero.

¡Así entienden que los datos en Gold no son números mágicos, sino respuestas a preguntas de negocio!
