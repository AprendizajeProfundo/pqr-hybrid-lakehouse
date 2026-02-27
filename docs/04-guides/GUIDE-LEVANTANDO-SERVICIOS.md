# Guía: Levantando los Servicios Locales con Docker Compose

**Versión:** 1.0  
**Fecha:** 2026-02-27  

Esta guía es una referencia rápida para levantar, verificar y detener la infraestructura local completa del Lakehouse (Control, Data, Compute y Serving Planes) utilizando Docker Compose.

---

## 1. Prerrequisitos Previos

Antes de ejecutar cualquier comando, asegúrate de que:
1. Tienes **Docker Desktop** instalado y ejecutándose en tu Mac.
2. Has creado tu archivo `.env` en la carpeta `infra/local/` con las variables de entorno necesarias (ver `GUIA-INFRA-LOCAL-DOCKER.md`).
3. No hay otros servicios ocupando los puertos clave en tu máquina local (5432, 9000, 4200, 3000, 3001, etc.).

---

## 2. Levantando la Infraestructura (El Arranque)

Sigue estos pasos paso a paso desde la terminal de tu sistema:

### Paso 2.1: Navegar al directorio de infraestructura
Debes ubicarte físicamente en la carpeta donde reside el archivo `docker-compose.yml`.

```bash
cd /Users/alvaromontenegro/Documents/Alvaro_2026/U_Sabana/pqr-hybrid-lakehouse/infra/local
```

### Paso 2.2: Consideraciones previas (Streamlit y Mac Apple Silicon)
Antes de levantar, asegúrate de haber considerado dos puntos clave para evitar errores:
1. **Streamlit Dockerfile:** Dado que el `docker-compose.yml` intenta construir (*build*) el contenedor de Streamlit, debes asegurarte de que exista la carpeta `apps/dashboard-streamlit` con un archivo `Dockerfile` y un `app.py` básico adentro (de lo contrario Docker lanzará el error *failed to read dockerfile*).
2. **Macs con Apple Silicon (M1/M2/M3):** Prefect usa una arquitectura Intel por defecto. Para que no falle, el `docker-compose.yml` debe tener la instrucción `platform: linux/amd64` debajo de `prefect-server` para obligar al chip a emularlo usando Rosetta.

### Paso 2.3: Iniciar los contenedores en segundo plano
Ejecuta el siguiente comando para leer el archivo compose y arrancar todos los servicios. 
- La bandera `-d` (detached) permite que los contenedores corran en segundo plano.
- La bandera `--build` le indica a Docker que debe construir la imagen de Streamlit primero.

```bash
docker-compose up -d --build
```
*(Nota: La primera vez que lo ejecutes puede tardar un poco mientras Docker descarga las imágenes base desde internet y construye Streamlit. Las ejecuciones posteriores serán casi instantáneas).*

---

## 3. Verificando el Estado (La Comprobación)

Una vez que el comando anterior finalice y te devuelva el control, verifica que todos los servicios estén en estado **"Up"**:

```bash
docker-compose ps
```

Deberías ver una salida filtrada similar a esta, indicando los nombres de los contenedores, su estado y los puertos expuestos:
```text
Name                           Command               State           Ports
-----------------------------------------------------------------------------------------------
dask-scheduler                 dask-scheduler ...    Up      0.0.0.0:8786->8786/tcp...
dask-worker-1                  dask-worker ...       Up      
dask-worker-2                  dask-worker ...       Up      
grafana                        /run.sh               Up      0.0.0.0:3001->3000/tcp
metabase                       /app/run_metabase.sh  Up      0.0.0.0:3000->3000/tcp
postgres                       docker-entrypoint...  Up      0.0.0.0:5432->5432/tcp
prefect-server                 prefect server ...    Up      0.0.0.0:4200->4200/tcp
prometheus                     /bin/prometheus ...   Up      0.0.0.0:9090->9090/tcp
rustfs                         /rustfs server ...    Up      0.0.0.0:9000->9000/tcp...
```

---

## 4. Accediendo a los Servicios (Los Puntos de Entrada)

Con la infraestructura sana y corriendo, puedes abrir tu navegador favorito y acceder a las interfaces de usuario de los distintos servicios:

| Servicio | Propósito | URL de Acceso Local | Credenciales por Defecto (Ver tu `.env`) |
| :--- | :--- | :--- | :--- |
| **Prefect UI** | Orquestación y flujos de trabajo | [http://localhost:4200](http://localhost:4200) | No requiere (para servidor local) |
| **Grafana** | Monitoreo y Observabilidad | [http://localhost:3001](http://localhost:3001) | Usuario: `admin` |
| **Metabase** | Business Intelligence y Dashboarding | [http://localhost:3000](http://localhost:3000) | Requiere configuración inicial en UI |
| **RustFS Console**| Interfaz gráfica de administración (S3) | [http://localhost:9001](http://localhost:9001) | `rustfsadmin` (o lo configurado) |
| **Dask Dashboard**| Monitoreo en vivo de procesamiento | [http://localhost:8787](http://localhost:8787) | No requiere |

Además, para conexiones por clientes de escritorio (DataGrip, DBeaver, Dask Client, etc.):
- **Postgres:** `localhost:5432` (Usuario: `postgres`)
- **Dask Scheduler:** `tcp://localhost:8786`
- **S3 API/Endpoint:** `localhost:9000`

---

## 5. Operaciones de Mantenimiento

### Ver los logs de un servicio específico
Si notas que un contenedor falla (se reinicia o está en estado 'Exited'), puedes inspeccionar sus logs:

```bash
docker-compose logs -f <nombre_del_servicio>
```
*Ejemplo:* `docker-compose logs -f postgres` o `docker-compose logs -f dask-worker`

### Detener la infraestructura sin destruir los datos
Cuando termines de trabajar y quieras apagar los servicios para liberar memoria en tu Mac, ejecuta:

```bash
docker-compose down
```
⚠️ **Importante:** Este comando elimina las redes y los contenedores, pero tus bases de datos, dashboards guardados y archivos subidos a RustFS seguirán existiendo intactos porque configuramos volúmenes (`volumes/`) en nuestro proyecto. Al hacer `up` nuevamente, todo estará exactamente donde lo dejaste.

### Detener y DESTRUIR datos (Limpieza Total)
Si cometiste un error irreversible en Postgres y quieres empezar la infraestructura desde cero nuevamente como si fuera el Día 1:

```bash
docker-compose down -v
```
⚠️ **Peligro:** La bandera `-v` (volumes) purga y destruye permanentemente tanto los contenedores como todo el almacenamiento local atado a ellos (Postgres y S3 caerán). Usar con extrema precaución.
