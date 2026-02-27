# Guía paso a paso: ¿Qué hace nuestro `docker-compose.yml`?

Este fichero describe todos los contenedores que se levantan juntos para simular la
infraestructura del proyecto. Docker Compose lo lee y crea una “mini‑nube” en tu
máquina.

---

## 1. Encabezado y versión

```yaml
version: '3.8'
```

- Indica la **versión de formato** de Compose; 3.8 es compatible con la mayoría
  de las funcionalidades modernas. No es una versión de software, sino del
  esquema de archivo.

---

## 2. Servicios (`services:`)

Cada bloque bajo `services` describe un contenedor diferente.

### 2.1 Control plane: Postgres

```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  volumes:
    - ./volumes/postgres-data:/var/lib/postgresql/data
    - ./init-scripts/init-postgres.sql:/docker-entrypoint-initdb.d/init.sql
  ports:
    - "5432:5432"
  networks:
    - pqr-network
```

- **image:** versión 15 del servidor PostgreSQL.
- **environment:** reemplaza `${...}` con valores del archivo `.env`; así no
  escribimos contraseñas en el código.
- **volumes:**
  - El primero guarda la base de datos en el disco del host (`./volumes/...`).
  - El segundo copia un script que corre al iniciar el contenedor (crea tablas,
    etc.).
- **ports:** expone el puerto 5432 para que tu equipo o aplicaciones externas
  puedan conectar.
- **networks:** se conecta a la red virtual `pqr-network` para hablar con otros
  servicios.

---

### 2.2 Data plane: RustFS (almacenamiento nativo)

```yaml
rustfs:
  image: rustfs/rustfs:latest
  container_name: rustfs
  restart: unless-stopped

  ports:
    - "9000:9000"   # S3 API endpoint
    # - "9001:9001" # admin/console si aplica

  environment:
    RUSTFS_ROOT_USER: ${RUSTFS_ACCESS_KEY}
    RUSTFS_ROOT_PASSWORD: ${RUSTFS_SECRET_KEY}

  volumes:
    - ./volumes/rustfs-data:/data

  networks:
    - pqr-network

  #command: ["server", "/data"]  # ajusta según tu versión
```

- Es el servidor de objetos S3 propio del proyecto.
- **Volumen:** `./volumes/rustfs-data` contiene todos los archivos de la capa
  “lakehouse”; si se borra, se pierde la información.
- **Credenciales:** se pasan como variables de entorno, el contenedor crea un
  usuario administrador con ellas.
- **Puertos:** el puerto 9000 es donde atiende la API S3; el 9001 suele ser la
  consola web (opcional).
- **restart:** reinicia el contenedor automáticamente si falla.

---

### 2.3 Compute plane: Dask

```yaml
dask-scheduler:
  image: daskdev/dask:latest
  command: dask-scheduler --host 0.0.0.0 --port 8786
  ports:
    - "8786:8786"
    - "8787:8787"
  networks:
    - pqr-network

dask-worker:
  image: daskdev/dask:latest
  command: dask-worker ${DASK_SCHEDULER_ADDRESS} --nprocs 2 --nthreads 1
  depends_on:
    - dask-scheduler
  deploy:
    replicas: 2
  networks:
    - pqr-network
```

- **Scheduler:** coordina tareas paralelas.
- **Worker(s):** ejecutan tareas; aquí se piden 2 procesos con 1 hilo cada uno y
  se despliegan dos réplicas.
- **depends_on:** asegura que el scheduler arranque antes de los workers.

---

### 2.4 Orquestación: Prefect Server

```yaml
prefect-server:
  image: prefecthq/prefect:latest
  command: prefect server start --host 0.0.0.0
  environment:
    PREFECT_API_URL: ${PREFECT_API_URL}
  ports:
    - "4200:4200"
  networks:
    - pqr-network
```

- Levanta la interfaz de Prefect para diseñar y monitorizar flujos de datos.

---

### 2.5 Observabilidad: Prometheus & Grafana

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
  networks:
    - pqr-network

grafana:
  image: grafana/grafana
  environment:
    GF_SECURITY_ADMIN_USER: ${GRAFANA_ADMIN_USER}
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD}
  volumes:
    - ./volumes/grafana-data:/var/lib/grafana
    - ./configs/grafana-dashboards:/var/lib/grafana/dashboards
  ports:
    - "3001:3000"
  networks:
    - pqr-network
```

- **Prometheus** recoge métricas; su configuración se monta desde el host.
- **Grafana** visualiza esas métricas; también persiste sus dashboards.

---

### 2.6 Serving: Streamlit & Metabase

```yaml
streamlit:
  build: ../../apps/dashboard-streamlit
  ports:
    - "${STREAMLIT_PORT}:8501"
  environment:
    SUPABASE_URL: ${SUPABASE_URL}
    SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
  networks:
    - pqr-network

metabase:
  image: metabase/metabase
  environment:
    MB_DB_TYPE: postgres
    MB_DB_HOST: postgres
    MB_DB_PORT: 5432
    MB_DB_USER: ${POSTGRES_USER}
    MB_DB_PASS: ${POSTGRES_PASSWORD}
    MB_DB_DBNAME: ${POSTGRES_DB}
  ports:
    - "${METABASE_PORT}:3000"
  depends_on:
    - postgres
  networks:
    - pqr-network
```

- **Streamlit** es el dashboard ejecutivo; se construye desde el código del proyecto.
- **Metabase** ofrece analítica de negocio; se conecta con la base de datos.

---

## 3. Redes (`networks:`)

```yaml
networks:
  pqr-network:
    driver: bridge
```

- Define una red virtual llamada `pqr-network`.
- Todos los servicios listados anteriormente están conectados a ella.
- Les permite encontrarse usando el nombre (`postgres`, `rustfs`, etc.) en vez
  de direcciones IP.

---

## 4. Volúmenes (`volumes:`)

```yaml
volumes:
  postgres-data:
  rustfs-data:
  grafana-data:
```

- Son “buckets” de datos gestionados por Docker.
- Se asignan en los servicios para mantener datos entre reinicios.
- En desarrollo es cómodo; para producción puedes reemplazarlos por mounts
  directos a discos físicos.

---

## 5. Cómo se arranca

1. Configura un archivo `.env` con todas las variables (`POSTGRES_USER`,
   `RUSTFS_ACCESS_KEY`, etc.).
2. En la terminal ve a la carpeta que contiene `docker-compose.yml`.
3. Ejecuta:

   ```bash
   docker-compose up -d
   ```

4. Docker descarga las imágenes y crea los contenedores. Verás en la consola
   que cada servicio inicia.
5. Usa `docker-compose ps` para ver el estado o `docker-compose logs -f <servicio>`
   para seguir los registros.

---

## 6. Qué ocurre detrás de escena

- Cada servicio corre en su propio contenedor aislado.
- Todos comparten la red `pqr-network`, así que pueden comunicarse internamente.
- Los puertos que expones (`ports:`) son para que **tu propio ordenador** o
  aplicaciones externas puedan acceder a los servicios.
- Los volúmenes guardan los datos fuera de los contenedores; si borras un
  contenedor los datos siguen ahí.

---

🎓 **Consejo para estudiantes:** puedes levantar este `docker-compose` en tu
máquina y probar comandos básicos como listar buckets S3, conectarte a la base
de datos o escribir una pequeña aplicación Python que use Dask. Es una forma
muy práctica de aprender cómo funciona un stack de datos moderno con contenedores.

¡Con esto tienen una guía clara y sencilla para entender y usar la configuración!