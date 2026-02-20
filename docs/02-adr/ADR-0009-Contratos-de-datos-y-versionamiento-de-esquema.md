# ADR-0009 — Contratos de datos y versionamiento de esquema

**Estado:** Aceptado  
**Fecha:** 2026-02-18

## Contexto
La ingestión y transformación puede sufrir drift (cambios de campos, tipos, reglas).
Sin contratos, el sistema se vuelve frágil y el BI pierde confiabilidad.

## Decisión
Definir y versionar contratos:

- **Raw:** JSON Schema con `schema_version`
- **Bronze/Silver/Gold:** especificaciones (MD o YAML) de columnas/tipos/reglas
- Validación de schema en pipeline (fail si incompatibilidad crítica)

Cambios incompatibles => nueva versión de contrato.

## Alternativas consideradas
- “Schema on read” sin contratos: drift silencioso.
- Contratos solo informales: difícil enforcement.

## Consecuencias
**Positivas**
- Datos confiables y reproducibles.
- Enseña ingeniería de datos profesional.
- Reduce incidentes en serving.

**Negativas**
- Trabajo inicial extra para escribir specs (vale la pena).

## Notas de implementación
- Validación Raw al leer (antes de Bronze).
- Validación Silver/Gold antes de carga a Postgres.