# Guía: Montando la Infraestructura PQR Hybrid Lakehouse en AWS

**Versión:** 1.0  
**Objetivo:** Transicionar del entorno local (`docker-compose.yml`) a un entorno de producción escalable y resiliente en Amazon Web Services (AWS).

Esta guía presenta un enfoque **Cloud-Native / Managed**, el cual reemplaza los contenedores genéricos con servicios administrados de AWS cuando sea posible (para disminuir la carga operativa) y utiliza orquestación de contenedores (ECS o EKS) para las cargas de trabajo personalizadas.

---

## 1. Arquitectura Recomendada (Mapeo Local a AWS)

En lugar de hacer un "Lift & Shift" (copiar los contenedores a servidores EC2), la mejor práctica empresarial es usar servicios administrados:

| Servicio Local | Rol | Componente en AWS | Justificación |
| :--- | :--- | :--- | :--- |
| **Postgres + PostGIS** | Control Plane / DWH | **Amazon RDS for PostgreSQL** (con extensión PostGIS) | Alta disponibilidad, backups automáticos, parcheo, y multi-AZ sin gestionar contenedores. |
| **RustFS** | Data Plane (Almacenamiento S3) | **Amazon S3** | S3 es el estándar de la industria. Reemplazo nativo perfecto y mucho más robusto. |
| **Dask Scheduler & Workers** | Compute Plane | **Amazon ECS (Fargate) o EKS** / **Amazon EMR on EKS** | ECS con autoscaling permite escalar dinámicamente ("spin up") trabajadores de Dask ante volumen. |
| **Prefect Server** | Orquestación | **Amazon ECS (Fargate)** | Servicio de contenedores serverless para web services. (Otra opción es Managed Prefect Cloud). |
| **Prometheus & Grafana** | Observabilidad | **Amazon Managed Service for Prometheus (AMP)** + **Amazon Managed Grafana** | Evita tener que mantener y escalar la infraestructura de monitoreo a mano. |
| **Metabase & Streamlit**| Serving / BI | **Amazon ECS (Fargate)** + **Application Load Balancer (ALB)**| Fargate corre los contenedores 24/7 sin gestionar servidores, ALB expone la interfaz segura (SSL). |

---

## 2. Paso a Paso de Implementación en AWS

A continuación, la secuencia lógica para desplegar esta infraestructura. Se recomienda encarecidamente emplear Infraestructura como Código (IaC) como **Terraform** o **AWS CDK**, en lugar de clicks manuales en la consola.

### Paso 0: Base IaC del repositorio (recomendado)
Ya existe un baseline Terraform en:

- `infra/aws/terraform/`

Incluye VPC, subredes, buckets S3 (`raw`/`refined`), repos ECR, ECS cluster, log groups y Secrets Manager.

Comandos base:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init -backend=false
terraform validate
terraform plan
```

Resultado esperado de validación:

```text
Success! The configuration is valid.
```

### Troubleshooting rápido Terraform

Si aparece:

```text
Error handling -chdir option: chdir infra/aws/terraform: no such file or directory
```

ejecuta:

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse
ls infra/aws/terraform
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform init -backend=false
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform validate
```

### Paso 1: Configuración de Red Base (Networking)
La base de la seguridad en la nube es la **VPC (Virtual Private Cloud)**.

1.  **Crear una VPC** (ej. `10.0.0.0/16`).
2.  **Subredes Públicas** (x2, en diferentes Availability Zones): Para el ALB (Load Balancer) y NAT Gateways.
3.  **Subredes Privadas** (x2): Donde realmente correrán los contenedores (Dask, Prefect, Metabase) y bases de datos (RDS).
4.  **Internet Gateway (IGW)** (en subred pública) y **NAT Gateway(s)** (en subred privada para dar salida a internet a los workers sin exponerlos directamente).

### Paso 2: Capa de Almacenamiento (Data Plane)
Reemplazaremos `RustFS` y `postgres-data` por servicios de almacenamiento nativos.

1.  **Crear Buckets S3:**
    *   `pqr-lakehouse-raw-{env}`: Datos crudos.
    *   `pqr-lakehouse-refined-{env}`: Datos transformados/limpios.
2.  Configurar **IAM Roles** (`ECS Task Roles` / `IRSA`) para que Dask y Prefect puedan leer/escribir en estos buckets asumiendo el rol, en lugar de usar access keys estáticas.

### Paso 3: Capa de Bases de Datos (Control Plane)
1.  **Crear base de datos Amazon RDS:**
    *   **Motor:** PostgreSQL v15.
    *   **Red:** Ubicada en los *Subnet Groups* privados.
    *   **Seguridad:** Un *Security Group* que solo acepte conexiones TCP por el puerto `5432` desde el *Security Group* de tus contenedores ECS/EKS.
2.  **Inicialización:** Conectarse temporalmente a la VPC (vía VPN, Session Manager, o EC2 Bastion) y ejecutar los scripts de `init-scripts/` para crear usuarios y la base de datos, y habilitar `CREATE EXTENSION postgis;`.

### Paso 4: Creación del Elastic Container Registry (ECR)
AWS ECR es el equivalente privado a Docker Hub.
1.  Crear repositorios para imágenes propias en ECR (ej. `pqr/streamlit-dashboard`).
2.  Hacer `docker build` y `docker push` de las aplicaciones personalizadas a estos repositorios (como Streamlit).
3.  *Opcional:* Hacer *pull-through cache* o clonar las imágenes públicas (Metabase, Prefect) a ECR para evitar límites de descarga de Docker Hub en producción.

### Paso 5: Orquestación y Cómputo (Amazon ECS)
Desplegaremos *Prefect*, *Metabase*, *Streamlit* y *Dask* en **Amazon Elastic Container Service (ECS)** con Fargate (serverless containers).

1.  **Crear ECS Cluster.**
2.  **Application Load Balancer (ALB):** Desplegado en redes **públicas**. Configurarlo para enrutar tráfico a los distintos servicios por dominio o prefijo (ej. `prefect.midominio.com`, `bi.midominio.com`).
3.  **Task Definitions y Servicios:**
    *   **Prefect Server:** Definir tarea basada en `prefecthq/prefect:3-latest`. Pasar la variable `PREFECT_API_URL` y conectar su base de datos al RDS. Enlazar al ALB por el puerto 4200.
    *   **Metabase:** Imagen `metabase/metabase`. Enlazar al ALB puerto 3000. Configurar las variables `MB_DB_*` apuntando a RDS.
    *   **Streamlit:** Imagen de tu ECR. Enlazar al ALB puerto 8501.
4.  **Dask Cluster (Cómputo):**
    *   *Opción Simple (ECS Fargate):* Un ECS Service para el *Dask Scheduler*. Para los workers, puedes pre-escalar N workers manualmente, o usar la librería Dask Cloud Provider para que el scheduler invoque nuevos contenedores Fargate bajo demanda.
    *   *Opción Avanzada (EKS):* Si requieres orquestación masiva y compleja de Jobs, Kubernetes con *Dask Operator* es el estándar.

### Paso 6: Observabilidad y Monitoreo
1.  **Amazon CloudWatch:** Configurar los logs de todos los contenedores (`awslogs` driver en las ECS Task Definitions) para que envíen sus logs a *CloudWatch Logs Groups*.
2.  **Amazon Managed Grafana:** Crear un workspace de Grafana.
3.  Configurar CloudWatch como *Data Source* en Grafana para ver métricas de CPU/RAM de RDS y ECS al instante.
4.  Si requieres métricas granulares internas de Dask, puedes habilitar **Amazon Managed Service for Prometheus (AMP)**, para que recolecte los endpoints expuestos `/metrics`.

---

## 3. Consideraciones Adicionales Importantes

*   **Seguridad y Secretos:** Reemplazar los archivos `.env` locales por **AWS Secrets Manager** o **AWS Systems Manager (SSM) Parameter Store**. En las *ECS Task Definitions*, puedes referenciar el ARN de un secreto y ECS lo inyectará como variable de entorno de forma segura durante el arranque del contenedor.
*   **Dominios y HTTPS:** Crear un certificado gratuito en **AWS Certificate Manager (ACM)** y adjuntarlo al Application Load Balancer (ALB) para garantizar que las UIs de Grafana, Prefect y Metabase carguen siempre por HTTPS.
*   **Costos:** Evitar correr bases de datos multi-AZ o NAT Gateways en los entornos de desarrollo/pruebas para ahorrar costos, restringiendo esto solo a Producción.

---

## 4. Checklist Go/No-Go (Previo a Push y Nube)

Marca `GO` solo si todos los puntos están en `OK`.

| Control | Evidencia mínima | Estado |
| :--- | :--- | :--- |
| Tests unitarios | `make test` -> `passed` | `OK/NO` |
| Terraform formato | `terraform -chdir=.../infra/aws/terraform fmt -check -recursive` sin cambios | `OK/NO` |
| Terraform válido | `terraform -chdir=.../infra/aws/terraform init -backend=false` + `validate` exitoso | `OK/NO` |
| Secrets saneados | Sin claves reales en repo (`rg -n "sk-proj-|AKIA|BEGIN PRIVATE KEY"`) | `OK/NO` |
| Guías alineadas | `GUIDE-DEPLOY-AWS.md` y `GUIDE-MIGRATION-LOCAL-TO-CLOUD.md` actualizadas | `OK/NO` |
| CI activo | Workflow `.github/workflows/ci.yml` presente | `OK/NO` |

### Criterio de decisión

1. Si todos los controles están en `OK` -> **GO** para:
   - actualizar GitHub,
   - iniciar despliegue cloud.
2. Si al menos uno está en `NO` -> **NO-GO** hasta corregir.

### Acta de ejecución (2026-03-06)

| Control | Evidencia ejecutada | Estado |
| :--- | :--- | :--- |
| Tests unitarios | `make test` -> `10 passed` | `OK` |
| Terraform formato | `terraform -chdir=infra/aws/terraform fmt -check -recursive` | `OK` |
| Terraform válido | `terraform -chdir=infra/aws/terraform init -backend=false && terraform -chdir=infra/aws/terraform validate` | `OK` (confirmado local por usuario: `Success! The configuration is valid.`) |
| Secrets saneados | `rg -n "sk-proj-|AKIA|BEGIN PRIVATE KEY" -S . --glob '!docs/04-guides/GUIDE-DEPLOY-AWS.md'` sin hallazgos | `OK` |
| Guías alineadas | `GUIDE-DEPLOY-AWS.md` + `GUIDE-MIGRATION-LOCAL-TO-CLOUD.md` actualizadas | `OK` |
| CI activo | `.github/workflows/ci.yml` presente | `OK` |

**Resultado consolidado (2026-03-06):** `GO` técnico (checklist completado, incluyendo validación Terraform local).

Plantilla para registrar cada corrida de validación:
- `docs/04-guides/TEMPLATE-ACTA-VALIDACION-PRE-NUBE.md`

Acta actual:
- `docs/04-guides/ACTA-VALIDACION-PRE-NUBE-2026-03-06.md`

### Cierre manual local pendiente de acta

Si ya tienes el mensaje:

```text
Terraform has been successfully initialized!
```

completa inmediatamente:

```bash
terraform -chdir=/Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/aws/terraform validate
```

y deja evidencia en el acta con:

- Fecha/hora de ejecución local
- Salida exacta: `Success! The configuration is valid.`
- Estado final de control `Terraform válido` = `OK`
