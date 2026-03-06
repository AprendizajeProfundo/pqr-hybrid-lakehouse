# GUIDE Terraform Baseline y Roadmap AWS

## 1) Objetivo
Esta guía documenta en detalle:
1. Lo que ya se implementó con Terraform en este repo.
2. Cómo validarlo y operarlo de forma segura.
3. Qué vamos a implementar después para pasar de baseline a despliegue cloud real.

Fecha de referencia: 2026-03-06.

---

## 2) Qué ya hicimos (estado actual)

### 2.1 Estructura IaC creada
Ruta principal:
- `infra/aws/terraform/`

Archivos:
1. `versions.tf` -> versión de Terraform y provider AWS.
2. `variables.tf` -> variables del proyecto (región, CIDR, subredes, NAT, repos ECR, logs).
3. `main.tf` -> recursos base.
4. `outputs.tf` -> salidas para integraciones posteriores.
5. `terraform.tfvars.example` -> plantilla de configuración por ambiente.
6. `README.md` -> guía operativa del baseline.

### 2.2 Recursos AWS del baseline
1. Red:
- VPC
- subredes públicas y privadas
- Internet Gateway
- route tables
- NAT opcional (`enable_nat_gateway`)

2. Data plane:
- S3 `raw`
- S3 `refined`
- versionado habilitado
- cifrado SSE (`AES256`)
- bloqueo público

3. Registro y cómputo base:
- ECR repos (`streamlit`, `metabase`, `prefect`, `dask`)
- ECS cluster

4. Operación y seguridad:
- CloudWatch log groups por servicio
- Secrets Manager (placeholders iniciales)

### 2.3 Cambios de gobernanza y seguridad alrededor de Terraform
1. `.gitignore` saneado para no versionar `.env` reales ni artefactos runtime.
2. `infra/local/.env` saneado (sin secreto real).
3. `infra/local/.env.example` y `.env.example` agregados.
4. CI agregado (`.github/workflows/ci.yml`) con:
- pruebas Python
- `terraform fmt`
- `terraform init -backend=false`
- `terraform validate`

---

## 3) Validación técnica mínima requerida (antes de nube)

Ejecutar desde tu máquina local:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
make test
terraform -chdir=infra/aws/terraform fmt -check -recursive
terraform -chdir=infra/aws/terraform init -backend=false
terraform -chdir=infra/aws/terraform validate
```

Resultado esperado:
1. Tests: `passed`.
2. Terraform `fmt`: sin cambios.
3. Terraform `validate`: `Success! The configuration is valid.`

---

## 4) Cómo aplicar el baseline en AWS (dev)

### 4.1 Preparar variables

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
```

Ajustar en `terraform.tfvars`:
1. `project_name`
2. `environment` (ej: `dev`)
3. `aws_region`
4. CIDRs según tu cuenta/red
5. `enable_nat_gateway` (costos)

### 4.2 Plan y apply

```bash
terraform init
terraform plan -out tfplan
terraform apply tfplan
```

### 4.3 Verificar outputs

```bash
terraform output
```

Debes registrar en acta:
1. `vpc_id`
2. `s3_raw_bucket`
3. `s3_refined_bucket`
4. `ecs_cluster_name`
5. `ecr_repository_urls`

---

## 5) Qué vamos a hacer después (roadmap Terraform)

## Fase A - Cerrar baseline operativo
1. Definir backend remoto de estado (S3 + DynamoDB lock) por ambiente.
2. Separar `dev/staging/prod` con archivos `.tfvars` por entorno.
3. Activar políticas de retención/lifecycle para buckets S3.
4. Endurecer tags y naming conventions obligatorias.

## Fase B - Despliegue de workloads
1. ECS Task Definitions:
- Streamlit
- Metabase
- Prefect server/worker
- Dask scheduler/worker

2. ALB + Target Groups + listeners HTTPS (ACM).
3. Security Groups por servicio con mínimo privilegio.
4. Inyección de secretos desde Secrets Manager en tareas ECS.

## Fase C - Capa de datos administrada
1. RDS PostgreSQL (subred privada, backups, parámetros).
2. SG de RDS solo desde SG de ECS.
3. Estrategia de inicialización SQL (`init-postgres.sql`) por job controlado.

## Fase D - Operación y resiliencia
1. Alarmas CloudWatch (CPU, memoria, errores, reinicios).
2. Dashboards operativos básicos.
3. Política de rollback documentada (`terraform plan` + versionado de módulos).
4. Control de costos (NAT, RDS sizing, log retention).

---

## 6) Criterios de aceptación para pasar a "inicio de nube"

Se autoriza inicio cloud cuando estén `OK`:
1. `make test`.
2. `terraform validate` local exitoso.
3. `plan` limpio y revisado por el equipo.
4. Secrets listos en Secrets Manager (sin secretos en git).
5. Checklist Go/No-Go en `GUIDE-DEPLOY-AWS.md` firmado en `GO`.

---

## 7) Troubleshooting rápido

### Error: `Error handling -chdir option ... no such file or directory`

Solución:
```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
ls infra/aws/terraform
```

Luego:
```bash
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform init -backend=false
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform validate
```

### Error: no conexión a `registry.terraform.io`

Causa típica:
1. DNS/red restringida.
2. Proxy corporativo no configurado.

Acción:
1. Ejecutar local fuera de sandbox/restricción.
2. Verificar conectividad DNS.

---

## 8) Referencias internas
1. `docs/04-guides/GUIDE-DEPLOY-AWS.md`
2. `docs/04-guides/GUIDE-MIGRATION-LOCAL-TO-CLOUD.md`
3. `infra/aws/terraform/README.md`
4. `.github/workflows/ci.yml`
5. `docs/04-guides/TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md`
