# Guía Conceptual: De Local a la Nube (AWS)

**Versión:** 1.0  
**Fecha:** 2026-02-27  

Esta guía explica conceptualmente cómo la infraestructura local que levantamos con Docker Compose se traduce y migra hacia un entorno de producción real en la nube, específicamente en AWS.

## El Concepto "Cloud-Native"
La arquitectura que estamos utilizando sigue una filosofía **Cloud-Native** y está preparada para Kubernetes (**K8s-ready**). Esto significa que tu código base (Python, consultas SQL, dashboards de Grafana) no requiere modificaciones para pasar de correr en tu Mac a correr en un clúster de producción con cientos de máquinas.

El `docker-compose.yml` que utilizamos localmente no es más que un simulador. Finge ser la nube para que puedas desarrollar y probar. Al momento de migrar, lo que cambia es **dónde** se ejecutan los servicios y **dónde** se guardan los datos, pero el "qué" y el "cómo" (el código) permanecen inmutables.

---

## 1. El Plano de Datos (Almacenamiento y Control)

Localmente, dependemos de volúmenes de Docker (`infra/local/volumes/`) atados a tu disco duro. En la nube, delegamos esta responsabilidad a servicios administrados para garantizar alta disponibilidad y evitar pérdida de datos.

### Base de Datos Relacional (El Control Plane)
* **Local:** Contenedor `postgres:15` escribiendo en `volumes/postgres-data`.
* **AWS:** Amazon RDS (Relational Database Service) para PostgreSQL o Amazon Aurora.
* **El Cambio:** 
  1. En tu archivo `.env`, cambias las variables `POSTGRES_HOST`, `POSTGRES_USER` y `POSTGRES_PASSWORD` para que apunten al Endpoint (URL) que AWS genera para tu nueva base de datos.
  2. Ejecutas el script de inicialización (`init-postgres.sql`) contra esa nueva URL.
  3. No hay contenedores que administrar; AWS se encarga de los backups, la replicación y el mantenimiento.

### Data Lake (El Data Plane)
* **Local:** Contenedor `rustfs` imitando el comportamiento de S3, escribiendo archivos Parquet, imágenes o audios en `volumes/rustfs-data`.
* **AWS:** Amazon S3 (Simple Storage Service).
* **El Cambio:**
  1. Cambias la variable `S3_ENDPOINT` en tu `.env` (o directamente usas el comportamiento por defecto de las librerías de AWS como `boto3`).
  2. Reemplazas las credenciales locales de RustFS por las Access Keys reales de AWS IAM.
  3. Tus scripts de Polars o Dask no se enteran del cambio, ya que ambos ecosistemas hablan el mismo idioma (S3 API).

---

## 2. El Plano de Cómputo (Procesamiento y Orquestación)

Localmente, todos los servicios pelean por los recursos (CPU y RAM) de tu máquina. En la nube, podemos escalar horizontalmente tanto como el presupuesto lo permita.

### Procesamiento Distribuido (Dask)
* **Local:** Contenedores `dask-scheduler` y `dask-worker` (escalados manualmente a 2 réplicas en Compose).
* **AWS:** Clústeres en Amazon EKS (Elastic Kubernetes Service) o frotas de contenedores en ECS (Elastic Container Service) usando Fargate (Serverless).
* **El Cambio:**
  1. Las **mismas imágenes Docker** que usamos localmente se publican en un registro (Amazon ECR).
  2. En lugar de Compose, configuras EKS/ECS para decirle: *"Levanta 1 Scheduler y 50 Workers de 16GB de RAM cada uno"*.
  3. Dask automáticamente descubrirá los nuevos workers y balanceará la carga de procesamiento (por ejemplo, al leer Terabytes de Parquet desde S3).

### Orquestación de Flujos (Prefect)
* **Local:** Contenedor `prefect-server` alojando la API y el UI en el puerto 4200.
* **AWS:** Podrías desplegar el servidor tú mismo en ECS, pero lo más sensato es usar **Prefect Cloud** (Software as a Service - SaaS).
* **El Cambio:** 
  1. Cambias la variable `PREFECT_API_URL` para que apunte a la nube y configuras la llave de API (API Key).
  2. Despliegas "Prefect Agents" o workers en tu cuenta de AWS (por ejemplo, en ECS) que escucharán las órdenes desde Prefect Cloud para ejecutar los scripts de Python.

---

## 3. El Plano de Servicio (Visualización y Analítica)

Las aplicaciones que exponen los resultados a los usuarios finales también migran de contenedores locales a servicios escalables.

### Dashboards y BI (Streamlit y Metabase)
* **Local:** Contenedores `streamlit` y `metabase` exponiendo puertos (8501 y 3000).
* **AWS:** AWS App Runner, ECS Fargate o incluso instancias EC2 básicas puestas detrás de un Balanceador de Carga (Application Load Balancer - ALB).
* **El Cambio:**
  1. Se suben las imágenes a Amazon ECR.
  2. Se configuran apuntando a la nueva base de datos RDS en lugar del Postgres local.
  3. El Balanceador de Carga les asigna un dominio público con certificado HTTPS.

### Observabilidad (Prometheus y Grafana)
* **Local:** Contenedores `prometheus` y `grafana` monitoreando Dask y el sistema.
* **AWS:** Amazon Managed Grafana y Amazon Managed Prometheus.
* **El Cambio:**
  1. AWS proporciona los servidores de Grafana y Prometheus listos para usar sin administrar infraestructura.
  2. Los servicios del clúster (EKS/ECS) se configuran para enviar sus métricas al Endpoint administrado de AWS.
  3. Importas el mismo archivo `.json` de tus tableros a la nueva interfaz.

---

## Resumen del Proceso de Migración

En resumen, la transición de Local a Cloud no implica un rediseño de la arquitectura, sino un reemplazo de plataformas:

| Componente | Desarrollo Local (Docker Compose) | Producción (AWS) | ¿Qué cambia en mi código? |
| :--- | :--- | :--- | :--- |
| **Código Base** | Archivos .py, .sql, dashboards | Mismos archivos | **Nada** |
| **Control Plane** | Contenedor `postgres` + Volúmenes | Amazon RDS (PostgreSQL) | Variables `.env` (URLs y credenciales) |
| **Data Plane** | Contenedor `rustfs` + Volúmenes | Amazon S3 | Variables `.env` de conexión S3 |
| **Compute Plane** | Contenedores `dask` | EKS (Kubernetes) o ECS Fargate | Manifiestos de despliegue (Helm/Terraform) |
| **Orquestación**| Contenedor `prefect-server` | Prefect Cloud | Variable `PREFECT_API_URL` y API Key |
| **Serving** | Contenedores `streamlit` / `metabase`| App Runner / ECS | URLs detrás de un Balanceador de Carga |
| **Monitoring** | Contenedores `prometheus` / `grafana` | Managed Grafana / Prometheus | Endpoints de recolección de métricas |

### Herramienta de Transición: Infraestructura como Código (IaC)

¿Cómo materializamos este cambio en el mundo real? Mientras localmente usamos `docker-compose up` para "prender" todo, en AWS no daremos clics en la consola. 

Se utilizarán herramientas como **Terraform** o **AWS CDK** para declarar estos recursos en código. De esta manera, construir la base de datos en RDS y levantar el clúster de ECS será tan reproducible y automatizado como levantar los contenedores en tu Mac.
