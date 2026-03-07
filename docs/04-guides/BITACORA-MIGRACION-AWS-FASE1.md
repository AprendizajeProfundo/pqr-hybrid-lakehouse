# Bitacora de Migracion AWS - Fase 1 (Ejecucion Real)

## 0) Proposito
Esta bitacora registra la ejecucion real de la migracion del proyecto a AWS (primera vez), sin omitir errores, dudas, decisiones ni comandos usados.

Objetivo Fase 1:
- Proyecto funcionando en nube con baseline Terraform aplicado y servicios base listos para siguiente despliegue de workloads.

Alcance Fase 1:
- Infraestructura base (VPC, subredes, S3, ECR, ECS cluster, Secrets Manager, logs).
- Validaciones tecnicas y checklist Go/No-Go ejecutado sobre entorno cloud.

Fuera de alcance Fase 1:
- Ajustes finos de performance y hardening avanzado.
- Pipeline de despliegue completo de todos los contenedores productivos.

---

## 1) Reglas de documentacion (obligatorias)
1. Registrar cada comando relevante ejecutado y su resultado.
2. Registrar cada error literal y su solucion exacta.
3. Registrar cada duda/pregunta del estudiante y su respuesta tecnica.
4. Registrar tiempos aproximados por hito.
5. Registrar decisiones y motivo (ejemplo: costo, seguridad, simplicidad).
6. Si se actualiza una guia, anotar archivo y razon del cambio.

Formato minimo por evento:
- `Fecha/Hora`
- `Paso`
- `Accion`
- `Comando`
- `Resultado`
- `Problema`
- `Solucion`
- `Aprendizaje`

---

## 2) Roadmap operativo inicial (Fase 1)

## Etapa A - Arranque controlado
1. Confirmar branch, estado git, guias vigentes.
2. Confirmar credenciales AWS activas (`aws sts get-caller-identity`).
3. Confirmar region objetivo y naming de ambiente (`dev`).

Entregable:
- Contexto de ejecucion y cuenta AWS confirmada.

## Etapa B - Terraform baseline
1. Revisar `infra/aws/terraform/terraform.tfvars` (o crear desde example).
2. Ejecutar `terraform init`.
3. Ejecutar `terraform plan` y revisar cambios esperados.
4. Ejecutar `terraform apply` con aprobacion consciente.
5. Capturar `terraform output`.

Entregable:
- Infra base creada en AWS y outputs registrados.

## Etapa C - Verificacion tecnica en AWS
1. Verificar VPC y subredes en consola.
2. Verificar buckets S3 (`raw` y `refined`) con bloqueo publico.
3. Verificar repos ECR creados.
4. Verificar ECS cluster y log groups.
5. Verificar Secrets Manager (secretos placeholders).

Entregable:
- Checklist tecnico de existencia y estado basico en `OK`.

## Etapa D - Prueba funcional minima de plataforma
1. Definir estrategia de primer servicio a subir (recomendado: Streamlit o Prefect).
2. Crear imagen y push a ECR del servicio piloto.
3. Crear task definition/servicio minimo en ECS (si entra en Fase 1 extendida).
4. Confirmar logs y salud basica del servicio.

Entregable:
- Primer workload visible corriendo en nube (si se ejecuta dentro de Fase 1 extendida).

## Etapa E - Cierre pedagogico
1. Consolidar errores reales y su solucion.
2. Actualizar guias impactadas.
3. Diligenciar acta final `GO/NO-GO` para pasar a siguiente fase.

Entregable:
- Bitacora cerrada y reutilizable por estudiantes.

---

## 3) Criterios de exito Fase 1
- Terraform aplicado sin errores criticos.
- Recursos baseline presentes y verificables en AWS.
- Sin secretos reales versionados en git.
- Evidencia reproducible para estudiantes (comandos + resultados + correcciones).

---

## 4) Riesgos esperados (primera vez)
1. Permisos IAM insuficientes.
2. Region/costos mal configurados.
3. Errores de naming global en S3.
4. Inconsistencias entre plan y apply.
5. Dudas de red (public/private subnets, NAT, security groups).

Mitigacion:
- Ejecutar por etapas, validar cada hito antes de continuar.

---

## 5) Plantilla de registro diario

### Entrada #001 (inicial)
- Fecha/Hora: 2026-03-06
- Paso: Inicio migracion real Fase 1
- Accion: Definicion de roadmap y reglas de bitacora
- Comando: N/A
- Resultado: Roadmap aprobado para ejecucion guiada
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Antes de ejecutar infraestructura, definir ruta y criterios evita retrabajo.

### Entrada #___
- Fecha/Hora:
- Paso:
- Accion:
- Comando:
- Resultado:
- Problema:
- Solucion:
- Aprendizaje:

---

## 6) Archivos relacionados
- `docs/04-guides/GUIDE-DEPLOY-AWS.md`
- `docs/04-guides/GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md`
- `docs/04-guides/GUIDE-MIGRATION-LOCAL-TO-CLOUD.md`
- `docs/04-guides/TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md`
- `docs/04-guides/ACTA-VALIDACION-PRE-NUBE-2026-03-06.md`


### Entrada #002
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Arranque controlado
- Accion: Verificacion de contexto local y autenticacion AWS
- Comando: `git branch --show-current && git status --short | wc -l`
- Resultado: `main` y `1` cambio pendiente en working tree
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Antes de nube, confirmar estado del repo evita confundir cambios locales con errores de despliegue.

### Entrada #003
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Credenciales AWS
- Accion: Validacion de identidad AWS
- Comando: `aws --version`, `aws sts get-caller-identity --output json`, `aws configure get region`
- Resultado: AWS CLI presente (`aws-cli/2.33.21`), pero `sts get-caller-identity` fallo con: `Unable to locate credentials. You can configure credentials by running "aws login".`
- Problema: No hay sesion AWS autenticada en esta terminal.
- Solucion: Ejecutar autenticacion (`aws login` o perfil SSO) y repetir `aws sts get-caller-identity`.
- Aprendizaje: El primer bloqueo real en migracion suele ser identidad/permisos, no Terraform.

### Pregunta abierta #001
- Pregunta: Que metodo de autenticacion usaremos para el curso (IAM Access Keys vs AWS SSO)?
- Recomendacion tecnica: AWS SSO para estudiantes (menos riesgo de llaves estaticas).
- Estado: Pendiente decision del equipo docente.

### Entrada #004
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Acompanamiento inicial
- Accion: Confirmacion de metodologia de registro completo
- Comando: N/A
- Resultado: Se confirma que toda la ejecucion se documenta en la bitacora, incluyendo preguntas y errores.
- Problema: Inquietud de seguimiento/documentacion del proceso.
- Solucion: Registrar explicitamente cada iteracion con evidencia y aprendizaje.
- Aprendizaje: La confianza del estudiante mejora cuando la trazabilidad se vuelve visible en tiempo real.

### Pregunta abierta #002
- Pregunta: "Espero que este guardando todo como quedamos".
- Respuesta tecnica: Si. Se registra cada paso, error, duda y decision en este archivo para su uso docente.
- Estado: Resuelta.

---

## 7) Recuperacion de trazabilidad (reconstruccion)

Esta seccion recupera el rastro pedagogico de la conversacion para no perder contexto de estudiante.

### Entrada #005
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Costo y plan inicial
- Accion: Consulta sobre plan gratuito y riesgo de costos por errores
- Comando: N/A (consulta conceptual)
- Resultado: Recomendacion de iniciar con plan gratuito/creditos y limitar riesgo con presupuesto + alertas + fases.
- Problema: Temor de costos inesperados en primera migracion.
- Solucion: Activar monitoreo/alertas de billing antes de crear recursos.
- Aprendizaje: En primera migracion, control de costos se configura antes que infraestructura.

### Entrada #006
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Facturacion IAM
- Accion: Aclaracion de "Acceso de usuario de IAM y rol a informacion de facturacion"
- Comando: N/A (consulta conceptual)
- Resultado: Se aclaro que habilita a usuarios/roles IAM para ver billing; no requiere usar root para operacion diaria.
- Problema: Ambiguedad de termino en consola AWS.
- Solucion: Explicacion y recomendacion de activarlo.
- Aprendizaje: Separar root de operacion diaria reduce riesgo operativo.

### Entrada #007
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Control de cuenta
- Accion: Aclaracion de mensaje "Cerrar cuenta"
- Comando: N/A (consulta conceptual)
- Resultado: Se confirmo que NO se debe cerrar la cuenta; se debe continuar con guardas de costo.
- Problema: Mensaje de consola interpretado como paso requerido.
- Solucion: Diferenciar opcion extrema (cerrar cuenta) vs configuracion de seguridad/costos.
- Aprendizaje: Validar significado de mensajes criticos antes de ejecutar acciones irreversibles.

### Entrada #008
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Checklist de preparacion de cuenta
- Accion: Definicion de pasos previos (MFA, IAM/SSO, billing IAM access, region, quotas)
- Comando: N/A (plan operativo)
- Resultado: Checklist entregado y confirmado en avance por estudiante.
- Problema: Falta de ruta concreta para primera iteracion.
- Solucion: Secuencia detallada de configuracion de cuenta.
- Aprendizaje: Un checklist corto elimina friccion al iniciar cloud por primera vez.

### Entrada #009
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Perfiles CLI
- Accion: Deteccion de perfil no relacionado (rustfs) y creacion de perfil AWS dedicado
- Comando recomendado: `aws configure sso --profile pqr-aws-dev`, `aws sso login --profile pqr-aws-dev`
- Resultado: Se definio estrategia de perfil separado para no mezclar credenciales.
- Problema: Perfil existente no aplicaba a AWS.
- Solucion: Crear perfil AWS exclusivo para migracion.
- Aprendizaje: Aislar credenciales por contexto evita errores de seguridad y despliegue.

### Entrada #010
- Fecha/Hora: 2026-03-06 14:53:07 -05
- Paso: Control de bitacora
- Accion: Solicitud del estudiante por perdida de rastro y recuperacion inmediata
- Comando: N/A
- Resultado: Se activa esta seccion de reconstruccion para trazabilidad completa.
- Problema: Percepcion de trazabilidad incompleta.
- Solucion: Consolidar eventos previos y estado actual en un solo bloque.
- Aprendizaje: La bitacora debe incluir tambien incidencias de seguimiento/documentacion.

### Estado actual (fin de recuperacion)
- Etapa A: En progreso.
- Bloqueante tecnico vigente: autenticacion AWS pendiente de validacion final con `aws sts get-caller-identity` en perfil AWS dedicado.
- Siguiente comando objetivo al retomar ejecucion:
  - `aws sts get-caller-identity --profile pqr-aws-dev`

### Entrada #011
- Fecha/Hora: 2026-03-06
- Paso: Etapa A - Ajuste de estrategia de autenticacion
- Accion: Cambio de SSO a IAM user para cuenta personal nueva
- Comando: N/A (decision operativa)
- Resultado: Se define flujo de autenticacion por Access Key + Secret Key en perfil AWS local.
- Problema: Flujo SSO pide `SSO start URL` y no aplica a cuenta personal recien creada sin Identity Center configurado.
- Solucion: Crear usuario IAM de trabajo con permisos controlados y configurar `aws configure --profile pqr-aws-dev`.
- Aprendizaje: En cuentas personales nuevas, IAM user es la ruta inicial mas directa; SSO queda para organizacion/curso multiusuario.

### Entrada #012
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Preparacion Terraform
- Accion: Verificacion/creacion de `terraform.tfvars`
- Comando: `test -f infra/aws/terraform/terraform.tfvars || cp infra/aws/terraform/terraform.tfvars.example infra/aws/terraform/terraform.tfvars`
- Resultado: Archivo `terraform.tfvars` listo con region `us-east-1`, ambiente `dev`, NAT desactivado.
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Congelar variables antes de plan evita drift y confusiones.

### Entrada #013
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Terraform init
- Accion: Inicializacion con perfil AWS dedicado
- Comando: `AWS_PROFILE=pqr-aws-dev AWS_REGION=us-east-1 terraform -chdir=infra/aws/terraform init`
- Resultado: Fallo con error literal: `Failed to query available provider packages` y `lookup registry.terraform.io: no such host`.
- Problema: El entorno de ejecucion no resuelve DNS hacia `registry.terraform.io`.
- Solucion: Ejecutar `init` desde terminal local del estudiante (fuera de sandbox/restriccion de red).
- Aprendizaje: Bloqueos de red del entorno pueden simular errores Terraform; validar conectividad primero.

### Entrada #014
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Terraform plan
- Accion: Intento de plan tras init fallido
- Comando: `AWS_PROFILE=pqr-aws-dev AWS_REGION=us-east-1 terraform -chdir=infra/aws/terraform plan -out=tfplan`
- Resultado: Fallo con `Failed to load plugin schemas` para provider AWS.
- Problema: Provider quedo parcial/inconsistente luego del fallo de descarga por DNS.
- Solucion: Limpiar directorio local Terraform y reintentar en terminal local con red funcional.
- Aprendizaje: Si init falla por red, el siguiente plan puede mostrar errores secundarios de plugin.

### Pregunta abierta #003
- Pregunta: Se puede continuar migration desde este entorno?
- Respuesta tecnica: No para `apply`; los comandos cloud deben correrse en terminal local con conectividad AWS y provider registry.
- Estado: Resuelta.

### Entrada #015
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Terraform init local
- Accion: Inicializacion en terminal local del estudiante con perfil AWS dedicado
- Comando: `terraform -chdir=infra/aws/terraform init`
- Resultado: `Terraform has been successfully initialized!`
- Problema: N/A
- Solucion: N/A
- Aprendizaje: La ejecucion local con conectividad normal resuelve el bloqueo de registry que aparecia en sandbox.

### Entrada #016
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Terraform plan local
- Accion: Generacion de plan de infraestructura baseline
- Comando: `terraform -chdir=infra/aws/terraform plan -out=tfplan`
- Resultado: `Plan: 33 to add, 0 to change, 0 to destroy`.
- Problema: N/A
- Solucion: N/A
- Aprendizaje: El plan esperado para Fase 1 es solo alta de recursos base (sin destrucciones).

### Evidencia resumida del plan
- Buckets esperados: `pqr-lakehouse-dev-raw`, `pqr-lakehouse-dev-refined`.
- ECS cluster esperado: `pqr-lakehouse-dev-ecs`.
- ECR esperado: `dask`, `metabase`, `prefect`, `streamlit`.
- Red esperada: VPC + subredes publicas/privadas.
- Secrets esperados: `db-master-password`, `grafana-admin-password`, `openai-api-key`, `supabase-jwt-secret`.

### Entrada #017
- Fecha/Hora: 2026-03-06
- Paso: Etapa B - Terraform apply local
- Accion: Aplicacion del plan baseline en AWS
- Comando: `terraform -chdir=infra/aws/terraform apply tfplan`
- Resultado: Aplicacion reportada como completada por el estudiante (pendiente captura textual del resumen final de Terraform).
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Ejecutar `apply` sobre `tfplan` reduce riesgo de cambios no revisados.

### Entrada #018
- Fecha/Hora: 2026-03-06
- Paso: Etapa C - Verificacion de outputs Terraform
- Accion: Captura de outputs de infraestructura creada
- Comando: `terraform -chdir=infra/aws/terraform output`
- Resultado: Outputs confirmados:
  - `vpc_id`: `vpc-076b2e868e0a5927c`
  - `ecs_cluster_name`: `pqr-lakehouse-dev-ecs`
  - `s3_raw_bucket`: `pqr-lakehouse-dev-raw`
  - `s3_refined_bucket`: `pqr-lakehouse-dev-refined`
  - `public_subnet_ids`: `subnet-05110c29f0d25b38d`, `subnet-0cf4bd6bf94314f2c`
  - `private_subnet_ids`: `subnet-0773b3625468501aa`, `subnet-0374b6b35f3ffe17a`
  - `ecr_repository_urls`: `dask`, `metabase`, `prefect`, `streamlit`
  - `secrets_arns`: `db-master-password`, `grafana-admin-password`, `openai-api-key`, `supabase-jwt-secret`
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Outputs versionados en Terraform permiten verificar la plataforma sin depender solo de consola.

### Entrada #019
- Fecha/Hora: 2026-03-06
- Paso: Etapa C - Verificacion S3/ECS/ECR
- Accion: Validacion cruzada por AWS CLI de recursos creados
- Comando:
  - `aws s3 ls | grep pqr-lakehouse-dev`
  - `aws ecs list-clusters`
  - `aws ecr describe-repositories --query 'repositories[].repositoryName' --output table`
- Resultado:
  - Buckets detectados: `pqr-lakehouse-dev-raw`, `pqr-lakehouse-dev-refined`
  - ECS detectado: `arn:aws:ecs:us-east-1:665303624774:cluster/pqr-lakehouse-dev-ecs`
  - ECR detectado: `pqr-lakehouse/dask`, `pqr-lakehouse/prefect`, `pqr-lakehouse/metabase`, `pqr-lakehouse/streamlit`
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Validar por CLI reduce errores de lectura visual en consola y deja evidencia reproducible.

### Cierre de Etapa C
- Estado: `OK`
- Decision: Baseline de infraestructura Fase 1 creado y verificado correctamente en AWS.

### Entrada #020
- Fecha/Hora: 2026-03-06
- Paso: Etapa C - Evidencia final de outputs
- Accion: Registro textual de outputs Terraform entregados por el estudiante
- Comando: `terraform -chdir=infra/aws/terraform output`
- Resultado: Se confirmaron IDs y nombres finales de VPC, subredes, buckets S3, cluster ECS, repos ECR y secretos.
- Problema: N/A
- Solucion: N/A
- Aprendizaje: Los outputs son el mapa maestro para navegar recursos en consola AWS sin perderse.

### Entrada #021
- Fecha/Hora: 2026-03-06
- Paso: Documentacion academica - Curso Maestro V2
- Accion: Creacion de version ampliada del curso maestro con indice integral de guias y trazabilidad al documento inicial del proyecto.
- Comando: Edicion documental en `docs/04-guides/CURSO_MAESTRO_PQR_LAKEHOUSE_V2.md`
- Resultado: Documento V2 generado con:
  - ruta de estudio de cero a nube,
  - introduccion por bloque tematico,
  - enlaces a todas las guias del catalogo `docs/04-guides`,
  - integracion de fuentes base en `docs/05-general-docs`.
- Problema: Riesgo de dispersion documental por guias en rutas diferentes.
- Solucion: Curaduria y centralizacion referencial en V2, incluyendo guias fuente copiadas en `docs/04-guides`.
- Aprendizaje: Un indice maestro reduce friccion para estudiantes y acelera onboarding tecnico.
