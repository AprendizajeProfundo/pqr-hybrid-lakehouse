# Terraform Baseline - AWS (PQR Hybrid Lakehouse)

Este baseline crea la base reproducible para el proyecto en AWS:
- Red: VPC, subredes publicas/privadas, IGW, route tables, NAT opcional.
- Data plane: buckets S3 `raw` y `refined` con cifrado + versionado + bloqueo publico.
- Compute baseline: ECS cluster.
- Registro de contenedores: ECR repos para `streamlit`, `metabase`, `prefect`, `dask`.
- Observabilidad base: CloudWatch log groups.
- Secretos: entradas iniciales en Secrets Manager.

## Requisitos

1. Terraform >= 1.6
2. Credenciales AWS activas (`aws configure` o variables de entorno)
3. Permisos IAM para VPC, S3, ECR, ECS, CloudWatch y Secrets Manager

## Uso

```bash
cd infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

## Costos y seguridad

- `enable_nat_gateway = false` por defecto para evitar costo fijo en ambientes de prueba.
- Para salida a internet desde subred privada habilita NAT y monitorea costo.
- No guardar secretos reales en `terraform.tfvars` ni en git.
- Poblar valores de secretos desde consola/CLI de AWS despues del `apply`.

## Alcance

Este baseline no crea aun servicios ECS ni RDS productivo; deja lista la plataforma para la siguiente etapa de despliegue de workloads.
