# CLASE LOCAL2AWS ALL

## 0. Objetivo de la clase
Llevar un proyecto de datos desde entorno local a AWS por primera vez, con control de costos, seguridad basica y evidencia tecnica reproducible.

Resultado esperado de esta clase:
- Infraestructura base creada en AWS con Terraform (Fase 1).
- Evidencia en consola y por CLI de recursos activos.
- Bitacora y checklist listos para auditoria y ensenanza.

---

## 1. Alcance
Incluye:
1. Preparacion local del proyecto.
2. Higiene de repo y GitHub.
3. Creacion y seguridad inicial de cuenta AWS.
4. Usuario IAM de trabajo (no root para operar).
5. Perfil AWS CLI.
6. Instalacion y uso de Terraform.
7. Ejecucion IaC: `init`, `plan`, `apply`.
8. Verificacion en AWS Console y CLI.
9. Cierre de fase y roadmap siguiente.

No incluye (en esta clase):
1. Despliegue completo de aplicaciones en ECS con ALB/HTTPS.
2. RDS productivo y migracion de datos completa.

---

## 2. Requisitos previos
1. Mac/Linux con terminal.
2. Docker instalado.
3. AWS CLI v2 instalado.
4. Terraform instalado.
5. Acceso al repositorio del proyecto.

Rutas del proyecto usadas en clase:
- `README.md`
- `docs/04-guides/GUIDE-PQR-HYBRID-LAKEHOUSE.md`
- `docs/04-guides/GUIDE-DEPLOY-AWS.md`
- `docs/04-guides/GUIDE-TERRAFORM-BASELINE-Y-ROADMAP.md`
- `docs/04-guides/BITACORA-MIGRACION-AWS-FASE1.md`
- `infra/aws/terraform/`

---

## 3. Fase Local (preparacion)

### 3.1 Verificar repo y entorno
Comandos:
```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
make env
make test
```

Objetivo:
- Confirmar que el proyecto corre local antes de moverlo a nube.

### 3.2 Higiene de secretos
1. Usar `infra/local/.env.example` como plantilla.
2. No versionar llaves reales.
3. Revisar `docs/04-guides/GUIDE-SEGURIDAD-SECRETS.md`.

---

## 4. Fase GitHub (control de cambios)
1. Confirmar que la documentacion y artefactos de IaC estan en el repo.
2. Mantener rama principal limpia.
3. Evitar subir datasets pesados no requeridos por la clase.

Comandos utiles:
```bash
git status --short
git branch --show-current
```

---

## 5. Creacion de cuenta AWS y seguridad inicial

### 5.1 Seguridad minima de cuenta
1. Activar MFA en root.
2. Configurar presupuesto y alertas de costo en Billing.
3. Habilitar IAM access a billing.
4. Elegir region unica de clase: `us-east-1`.

### 5.2 Usuario IAM de trabajo
Crear usuario `pqr-aws-dev` con permisos iniciales de arranque.

Recomendacion didactica:
- Para primera clase: permisos amplios controlados temporalmente.
- Para siguientes clases: reducir a minimo privilegio.

### 5.3 Access keys para CLI
Generar desde IAM User -> `Security credentials` -> `Create access key` para CLI.

---

## 6. AWS CLI perfil dedicado
No mezclar perfiles de otras herramientas (ejemplo: rustfs).

Configurar perfil:
```bash
aws configure --profile pqr-aws-dev
```

Valores:
- Access Key ID: generado en IAM
- Secret Access Key: generado en IAM
- Region: `us-east-1`
- Output: `json`

Validar identidad:
```bash
aws sts get-caller-identity --profile pqr-aws-dev
```

Si responde con `UserId`, `Account`, `Arn`, la autenticacion esta correcta.

Que es ARN:
- `ARN` (Amazon Resource Name) es el identificador unico de una identidad o recurso en AWS.

---

## 7. Terraform: que es y para que sirve
Terraform es IaC (Infrastructure as Code): defines infraestructura en codigo versionable y reproducible.

Beneficios clave:
1. Repetible: mismo resultado en distintos entornos.
2. Auditado: cambios quedan en git.
3. Controlado: `plan` antes de `apply`.
4. Escalable: base para CI/CD y ambientes dev/staging/prod.

Instalacion (macOS/Homebrew):
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
terraform -version
```

---

## 8. Preparar IaC del proyecto

### 8.1 Ir al directorio Terraform
```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform
```

### 8.2 Crear variables de entorno
```bash
cp terraform.tfvars.example terraform.tfvars
```

Valores usados en clase:
- `project_name = "pqr-lakehouse"`
- `environment = "dev"`
- `aws_region = "us-east-1"`
- `enable_nat_gateway = false` (control de costos)

### 8.3 Validaciones previas
```bash
terraform fmt -check -recursive
terraform init
terraform validate
```

---

## 9. Ejecutar despliegue Fase 1

### 9.1 Plan
```text
Ejecutamos en la terminal
```
```bash
export AWS_PROFILE=pqr-aws-dev
export AWS_REGION=us-east-1

rm -rf infra/aws/terraform/.terraform
rm -f infra/aws/terraform/tfplan

terraform -chdir=infra/aws/terraform init
terraform -chdir=infra/aws/terraform plan -out=tfplan
```
```text
Resultado observado en clase:
- `Plan: 33 to add, 0 to change, 0 to destroy`
```
### 9.2 Apply
```bash
AWS_PROFILE=pqr-aws-dev 
AWS_REGION=us-east-1 
terraform apply tfplan
```

### 9.3 Output
```bash
terraform output
```

Recursos confirmados en clase:
1. VPC
2. 2 subredes publicas + 2 privadas
3. Buckets S3 `pqr-lakehouse-dev-raw` y `pqr-lakehouse-dev-refined`
4. Cluster ECS `pqr-lakehouse-dev-ecs`
5. Repos ECR: `dask`, `metabase`, `prefect`, `streamlit`
6. Secrets Manager (4 secretos base)

---

## 10. Verificacion en AWS Console
Con region `us-east-1`:
1. VPC -> Your VPCs (ID esperado del output)
2. VPC -> Subnets
3. S3 -> Buckets
4. ECS -> Clusters
5. ECR -> Repositories
6. Secrets Manager -> Secrets
7. Billing -> Cost Explorer / Budgets / Free Tier

Verificacion por CLI:
```bash
aws s3 ls | grep pqr-lakehouse-dev
aws ecs list-clusters
aws ecr describe-repositories --query 'repositories[].repositoryName' --output table
```

---

## 11. Errores reales de la clase y solucion

### Error 1
`Unable to locate credentials. You can configure credentials by running "aws login"`

Causa:
- No habia credenciales AWS CLI activas.

Solucion:
- Crear Access Key/Secret Key de usuario IAM y configurar perfil `pqr-aws-dev`.

### Error 2
`Failed to query available provider packages` + `lookup registry.terraform.io: no such host`

Causa:
- Restriccion de red del entorno donde se ejecuto comando.

Solucion:
- Ejecutar Terraform en terminal local con conectividad normal.

### Error 3
Confusion entre usuario/clave de consola y Access Key CLI.

Causa:
- IAM Console password no sirve para `aws configure`.

Solucion:
- Crear `Access key` tipo CLI desde `Security credentials` del usuario IAM.

---

## 12. Artefactos de evidencia de clase
1. `docs/04-guides/BITACORA-MIGRACION-AWS-FASE1.md`
2. `docs/04-guides/TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md`
3. `docs/04-guides/ACTA-VALIDACION-PRE-NUBE-2026-03-06.md`
4. Outputs de Terraform y verificaciones CLI capturadas.

---

## 13. Roadmap siguiente (post Fase 1)

### Fase 2
1. Publicar primera imagen a ECR (streamlit o prefect).
2. Crear task definition ECS y servicio minimo.
3. Verificar logs en CloudWatch.

### Fase 3
1. ALB + HTTPS (ACM).
2. RDS PostgreSQL en subred privada.
3. Inyeccion de secretos reales desde Secrets Manager.

### Fase 4
1. Endurecer IAM a minimo privilegio.
2. Backend remoto Terraform (state en S3 + lock).
3. FinOps: alertas, dashboards de costo, cleanup automatizado.

---

## 14. Cierre de clase
Si llegaste hasta aqui, lograste:
- preparar local,
- configurar cuenta AWS segura para primera iteracion,
- autenticar CLI,
- aplicar IaC real,
- validar recursos en consola y CLI,
- y documentar el proceso para ensenanza.

Siguiente clase recomendada:
- "Fase 2: primer servicio en ECS desde imagen ECR".
