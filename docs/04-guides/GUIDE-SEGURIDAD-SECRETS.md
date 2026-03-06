# Guia de Seguridad de Secretos

## Reglas base

1. No guardar secretos reales en archivos versionados.
2. Usar `.env.example` con placeholders.
3. En AWS usar Secrets Manager o SSM Parameter Store.
4. Rotar secretos inmediatamente si se exponen en texto plano.

## Acciones aplicadas en este repo

1. `infra/local/.env` fue saneado para eliminar valor real de `OPENAI_API_KEY`.
2. Se agrego `infra/local/.env.example` para configuracion segura por plantilla.
3. Se normalizo `.gitignore` para ignorar `.env` y artefactos runtime.

## Accion manual pendiente (obligatoria)

Si una clave real fue expuesta en historial local o remoto:

1. Revocar y regenerar la clave en el proveedor (OpenAI/AWS/etc).
2. Reemplazar el secreto en entornos locales y cloud.
3. Eliminar evidencia historica en git solo si el secreto llego a remoto.
4. Confirmar que CI/CD consume secretos desde almacenamiento seguro.
