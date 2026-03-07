# Curso Maestro: PQR Hybrid Lakehouse - De Cero a la Nube (AWS)

Bienvenido a la guía educativa definitiva del proyecto **PQR Hybrid Lakehouse**. Este documento está diseñado como una herramienta pedagógica (paso a paso) para entender a profundidad qué conforma este repositorio, cómo funcionan sus componentes locales y cuál es la estrategia y el progreso actual de su despliegue a Amazon Web Services (Fase I completada).

---

## Índice del Curso
1. [Módulo 1: Entendiendo la Arquitectura y el Repositorio](#módulo-1-entendiendo-la-arquitectura-y-el-repositorio)
2. [Módulo 2: Entorno Local e Infraestructura Base](#módulo-2-entorno-local-e-infraestructura-base)
3. [Módulo 3: Generación de Datos y Arquitectura Medallón (ETL)](#módulo-3-generación-de-datos-y-arquitectura-medallón-etl)
4. [Módulo 4: Orquestación y Analítica de Consumo](#módulo-4-orquestación-y-analítica-de-consumo)
5. [Módulo 5: Migración a AWS - Fase I (La Base en la Nube)](#módulo-5-migración-a-aws---fase-i-la-base-en-la-nube)
6. [Módulo 6: El Rumbo Futuro (Roadmap de Nube)](#módulo-6-el-rumbo-futuro-roadmap-de-nube)

---

## Módulo 1: Entendiendo la Arquitectura y el Repositorio

El proyecto implementa una **Arquitectura Híbrida por Planos** que separa las responsabilidades del sistema:
- **Plano de Datos:** Un *Lakehouse* (Almacenamiento en S3/RustFS) que organiza los datos en capas (Raw, Bronze, Silver, Gold).
- **Plano de Control/Serving:** Bases de datos relacionales (Postgres) que manejan metadatos, configuraciones de la aplicación y la exposición final para los Dashboards.
- **Plano de Cómputo:** ETLs en Python, orquestación, y motores de transformación de datos.

### Estructura del Repositorio
Al observar la raíz del proyecto, encontramos carpetas con objetivos delimitados:
- `apps/`: Contiene el código fuente de los pipelines ETL (`pipelines/`), los simuladores de datos (`simulator/`), y la aplicación de análisis (`dashboard-streamlit/`).
- `data/`: Almacena los resultados locales físicos divididos por capas del Lakehouse (raw, bronze, silver, gold).
- `infra/`: Código de infraestructura. Posee `local/` para levantar contenedores vía Docker Compose y `aws/terraform` para el aprovisionamiento como código (IaC) en la nube.
- `docs/`: Documentación, minutas de reuniones (ADRs - Architecture Decision Records), y guías específicas.
- `Makefile`: **El cerebro de las operaciones locales.** Permite disparar comandos comunes sin recordar secuencias complejas.

---

## Módulo 2: Entorno Local e Infraestructura Base

Para empezar a trabajar con el proyecto, el primer paso es aislar las dependencias y levantar las herramientas base de datos locales.

**Paso a paso:**
1. **Creación del entorno de trabajo:**  
   Se usa `Conda` junto con el `Makefile`. Al ejecutar:
   ```bash
   make env
   ```
   Se lee el archivo `environment.yml` instalando las librerías necesarias (pandas, prefect, streamlit, pytest, etc.).

2. **Validación del entorno:**
   ```bash
   make test
   ```
   Esto asegura que el código principal base y los tests funcionales pasen exitosamente (código libre de errores iniciales).

3. **Infrastructura de Servicios Locales:**  
   En `infra/local/docker-compose.yml`, se encuentran los servicios esenciales: *Postgres* (Base de Datos), *Prefect Server* (Orquestador ETL), y *Metabase* (BI).
   ```bash
   cd infra/local
   cp .env.example .env  # Configurar variables secretas
   docker-compose up -d
   ```

> [!TIP]
> Recuerda que no se deben subir claves secretas o passwords (archivos `.env`) al repositorio. Esto es vital tanto en local como en la nube.

---

## Módulo 3: Generación de Datos y Arquitectura Medallón (ETL)

El proyecto simula eventos PQRS (Peticiones, Quejas, Reclamos y Sugerencias).

**El Ciclo de Vida del Dato:**

1. **Simulación (Generación Raw):**  
   Scripts en `apps/simulator` crean eventos sintéticos simulando el tráfico real del sistema en formato `JSONL` (JSON Lines).
2. **Ingesta y Capa Raw:**  
   `make etl-ingest` lee el archivo `JSONL` y consolida el inicio del proceso en nuestro almacenamiento Lakehouse.
3. **Capa Bronze:**  
   `make etl-bronze` procesa los datos crudos, estandariza esquemas, añade metadatos (como `run_id` para *trazabilidad*) y separa los registros fallidos o corruptos.
4. **Capa Silver:**  
   `make etl-silver` filtra anomalías de negocio y efectúa agregaciones e imputaciones leves. Es la "fuente de la verdad".
5. **Capa Gold:**  
   `make etl-gold` prepara los datos para consumo directo (ej. calculando métricas de niveles de servicio (SLA), resúmenes dimensionales para mapas temporales y espaciales).
6. **Carga al Plano de Control (Postgres):**  
   `make etl-load` toma los datos pre-calculados Gold y los inserta tablas de Postgres a ser consultadas por los Dashboards a alta velocidad.

---

## Módulo 4: Orquestación y Analítica de Consumo

Lanzar cada paso por separado con `make etl-...` es útil para debugear, pero en la vida real necesitamos orquestador automatizado.

### 1. Prefect (El Orquestador)
El pipeline completo se engloba dentro de **Prefect** en el script `apps/pipelines/prefect_etl_flow.py`. Al ejecutar:
```bash
make etl-flow
```
Prefect maneja la dependencia de tareas, genera gráficos de ejecución y reintenta pasos fallidos automáticamente permitiendo una auditoría limpia.

### 2. Dashboards de Análisis (El Consumo)
Teniendo la BD Postgres con la Data Gold calculada, el proyecto expone sus insights usando:
- **Streamlit (`make dashboard-app`):** Una aplicación analítica programada en Python.
- **Metabase:** Un motor autónomo de exploración analítica donde se construyen visualizaciones arrastrando métricas sin código base.

---

## Módulo 5: Migración a AWS - Fase I (La Base en la Nube)

Moverse de local a AWS requiere disciplina. Como documentado en la Bitácora de Migración Fase 1, se cumplió un hito muy importante: **Aprovisionar la Infraestructura Base como Código usando Terraform**.

**Resumen Pedagógico de lo que YA se implementó (Fase I):**

1. **Gestión de Identidad (IAM):**
   Se creó un usuario de trabajo (ej. `pqr-aws-dev`), con credenciales propias (Access key / Secret key) y se configuró perfil AWS CLI propio. 
   *(Lección: Nunca se trabaja ni se despliega usando el usuario `root`)*.

2. **Infraestructura como Código (IaC - Terraform):**
   El código en `infra/aws/terraform/` definió todos los servicios bajo la premisa del control (*Plan antes del Apply*).
   - `terraform init`: Para bajar las librerías del proveedor AWS.
   - `terraform plan -out=tfplan`: Para auditar qué creará la herramienta antes de crearla.
   - `terraform apply`: Para provisionar.

3. **Artefactos Creados en Fase I:**
   - **VPC y Redes:** Se creó 1 Red Virtual aislada (VPC) con 2 subredes públicas y 2 privadas. Se estructuró el terreno sobre el cual vivirán las aplicaciones.
   - **Buckets S3 (Lakehouse Cloud):** Se construyeron los buckets `pqr-lakehouse-dev-raw` y `pqr-lakehouse-dev-refined`. *El Lakehouse local ahora tiene asilo en la nube*.
   - **Cluster ECS (`pqr-lakehouse-dev-ecs`):** El entorno donde correrán los contenedores Docker en un futuro.
   - **Repositorios ECR:** El "Docker Hub" privado de AWS. Se crearon repos para `dask`, `metabase`, `prefect` y `streamlit`.
   - **Secrets Manager:** El equivalente a nuestro `.env` local, ahora alojado de forma encriptada.

> [!IMPORTANT]
> La **Fase I fue un éxito** porque se logró establecer esta base usando un método de automatización puro sin recurrir a la consola manual. Al final del despliegue se validó la existencia de todos los recursos (via CLI (`aws s3 ls`, `aws ecr describe-repositories`)).

---

## Módulo 6: El Rumbo Futuro (Roadmap de Nube)

Ahora que la casa está construida (Fase I), lo que sigue es decorarla y habitarla. 

**Próximos pasos recomendados (Fases II y III):**

1. **Subir los contenedores (Empaquetamiento a ECR):**
   Tomar el código (ej. el dashboard de Streamlit), construir la imagen de Docker, y aplicar un push al repositorio ECR ya existente.
2. **Workloads en ECS / Fargate:**
   Crear "Task Definitions" de AWS para indicarle al cluster ECS recién creado que levante y ejecute la aplicación (Streamlit o Prefect) leyendo las variables de Secrets Manager.
3. **Plano de Control Confiable (RDS Postgres):**
   En vez de un contenedor efímero, instanciar un Amazon RDS de PostgreSQL en una de las subredes *privadas* de la VPC generada en Fase 1, y redirigir los pipelines Gold de Prefect hacia este servidor manejado.
4. **Navegación al Público (ALB + HTTPS):**
   Agregar un *Application Load Balancer (ALB)* al frente para permitir que los usuarios exploren los Dashboards a través de una URL segura HTTPS.

> **¡Felicidades!** Estás comprendiendo profundamente no solo un proyecto de analítica avanzada o de machine learning; estás observando la creación sistemática de una arquitectura moderna lista para la empresa.
