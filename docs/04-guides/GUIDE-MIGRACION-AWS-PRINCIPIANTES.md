# Guía de Migración a AWS para Principiantes absolutos

**Objetivo:** Llevar tu proyecto local (que corre con `docker-compose`) a la nube de AWS por primera vez, sin estrés y entendiendo cada paso.

Si nunca has tocado AWS, ver todos sus servicios (tienen más de 200) puede ser abrumador. ¡No te preocupes! Para empezar, solo necesitamos enfocarnos en **uno** o **dos** conceptos.

---

## 🎧 Conceptos Básicos: "Traduciendo a Español"

Antes de tocar la consola, hagamos un glosario rápido:

*   **AWS (Amazon Web Services):** Es simplemente "la computadora de alguien más" (la de Amazon) que puedes alquilar por horas.
*   **EC2 (Elastic Compute Cloud):** Es una computadora virtual. Imagina que es un computador normal (con su CPU, RAM y disco duro) al que te conectas por internet. Aquí es donde vivirá tu Docker.
*   **Security Group (Grupo de Seguridad):** Es el vigilante de la puerta (Firewall). Le dice a tu computador en la nube qué puertos dejar abiertos (ej. dejar pasar a la gente al puerto 3001 de Grafana) y qué puertos cerrar.
*   **RDS (Relational Database Service):** Es una base de datos Postgres, pero en lugar de instalarla tú, Amazon la instala, la cuida y le hace copias de seguridad. (Lo usaremos más adelante).

---

## 🚀 El Plan: "Lift & Shift" (Copiar y Pegar)

> Alcance de seguridad: esta guía es para **demo/controlado**.  
> Para producción usa la guía cloud-native con IaC (`docs/04-guides/GUIDE-DEPLOY-AWS.md`) y no expongas puertos directamente a internet.

La forma más fácil y recomendada para tu **primera vez** no es usar 50 servicios distintos. La forma más fácil es alquilar una máquina (EC2), instalar Docker en ella y correr tu `docker-compose.yml` exactamente igual que en tu computador. A esto se le llama "Lift & Shift".

### Paso 1: Crear tu cuenta de AWS y entrar

1. Ve a [aws.amazon.com](https://aws.amazon.com/es/) y crea una cuenta. (Te pedirá una tarjeta de crédito, pero tienen un nivel gratuito llamado *Free Tier* por un año para cosas pequeñas. Dado que tu proyecto es grande, probablemente requieras una máquina que cobre un poco).
2. Tarda un rato en activarse. Una vez activada, entra a la **Consola de Administración de AWS** (AWS Management Console).

### Paso 2: Crear tu "Computador en la Nube" (Instancia EC2)

1. En la barra de búsqueda superior, escribe **EC2** y haz clic en el primer resultado.
2. Busca el botón naranja gigantesco que dice **"Lanzar instancia" (Launch Instance)**. Haz clic.
3. Ponle un nombre, por ejemplo: `Servidor-PQR-Lakehouse`.
4. En **Imágenes de SO (AMI)**, elige **Ubuntu** (es el sistema operativo más amigable para instalar Docker). Deja la versión que diga "Free tier eligible" o LTS.
5. En **Tipo de instancia** (el tamaño del computador), para correr todo tu entorno (Postgres, Dask, Prefect, Metabase, etc.) vas a necesitar algo de RAM. Elige al menos una **`t3.large`** (8 GB de RAM) o **`t3.xlarge`** (16 GB). *Nota: Esto te cobrará algunos centavos por hora mientras esté prendida*.
6. En **Par de claves (Key pair)**, haz clic en "Crear nuevo par de claves". Ponle el nombre `PQR-llave`. Descarga el archivo `.pem` y guárdalo muy bien en tu computador, es tu "llave" para entrar al servidor.
7. Haz clic en el botón naranja: **Lanzar instancia**.

### Paso 3: Abrir las "Puertas" (Configurar el Security Group)

Tu servidor ya existe, pero por defecto nadie puede ver tus aplicaciones. Hay que abrir los puertos.

1. Ve a la lista de "Instancias" en EC2 y haz clic en la que acabas de crear.
2. Abajo, en las pestañas, ve a **Seguridad (Security)** y haz clic en el enlace azul del Grupo de Seguridad (ej. `sg-0abc123...`).
3. Ve a **Reglas de entrada (Inbound rules)** y haz clic en "Editar reglas de entrada".
4. Agrega reglas para permitir tráfico ("Custom TCP") desde **tu IP pública** (`My IP`) para los puertos de tus aplicaciones:
    *   Puerto `3001` (Grafana)
    *   Puerto `3000` (Metabase)
    *   Puerto `4200` (Prefect)
    *   Puerto `8501` (Streamlit - si aplica)
5. Guarda las reglas.
6. Para producción, evita abrir puertos de administración/UI y publica servicios detrás de ALB + HTTPS.

### Paso 4: Conectarte a tu Servidor e Instalar Docker

1. Vuelve a la lista de "Instancias". Selecciona tu instancia y arriba haz clic en el botón **Conectar (Connect)**.
2. Tienes dos opciones fáciles: usar la pestaña **EC2 Instance Connect** (te abre una terminal directo en el navegador de internet, es la más fácil) o conectarte por SSH usando la llave `.pem` que descargaste en el paso 2. Usemos "EC2 Instance Connect". Haz clic en conectar.

3. ¡Felicidades! Estás dentro de la terminal de tu computador en la nube. Ahora, instala Docker copiando y pegando estos comandos uno por uno, presionando Enter:
    ```bash
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-v2 git
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker ubuntu
    ```
4. *Cierra esa ventana del navegador y vuelve a hacer clic en "Conectar" para que los cambios de permisos surtan efecto.*

### Paso 5: Traer tu código al servidor

1. De vuelta en la terminal del servidor, clona tu repositorio de código (desde un GitHub donde lo tengas subido, por ejemplo):
    ```bash
    git clone https://github.com/TU_USUARIO/TU_REPO.git
    cd TU_REPO/infra/local
    ```
2. Revisa que estén tus archivos: `ls -la`
3. Si utilizabas un archivo `.env` con contraseñas en tu computador, deberás crearlo aquí en el servidor:
    ```bash
    nano .env
    ```
    (Copia y pega tus variables ahí, presiona `Ctrl+X`, luego `Y`, y luego `Enter` para guardar).
4. Nunca subas ese `.env` a GitHub. Para producción usa AWS Secrets Manager o SSM Parameter Store.

### Paso 6: ¡Que se haga la magia!

1. Con todo listo, ejecuta el mismo comando que usabas en tu computador:
    ```bash
    docker compose up -d
    ```
2. Espera unos minutos a que descargue todo y levante los servicios.

### Paso 7: Entrar a tus aplicaciones

1. Ve a la consola de EC2 de Amazon, selecciona tu instancia y busca tu **Dirección IPv4 pública** (Public IPv4 address), será algo como `3.15.42.100`.
2. Ve a la barra de direcciones de tu navegador de internet en tu compu, y entra a tus servicios combinando esa IP con los puertos que abrimos:
    * Para Grafana: `http://TU_IP:3001`
    * Para Prefect: `http://TU_IP:4200`
    * Para Metabase: `http://TU_IP:3000`

---

## 🔮 Fase 2: Evolucionando a un Nivel Profesional

El "Paso a Paso" anterior te da una victoria rápida: tu proyecto ya corre en la nube para que puedas mostrárselo a quien quieras.

Sin embargo, para un proyecto "serio" o "empresarial", tener todo en un solo computador EC2 no es seguro (si el EC2 se apaga, se daña o se llena el disco duro, pierdes la base de datos). 

**Cuando te sientas cómodo con el paso anterior, harás este cambio:**

1. Entras a la consola de AWS, buscas **RDS** y creas una base de datos (PostgreSQL). AWS te dará una URL (ej. `mi-base.amazon.com:5432`).
2. Entras a tu servidor EC2 y cambias tu `.env` o tu `docker-compose.yml` para que ya NO levante un contenedor de base de datos. En su lugar, apuntas `MB_DB_HOST` y el resto de las aplicaciones a la URL que te dio Amazon RDS.
3. Haces lo mismo con **Amazon S3**: en lugar de correr un contenedor de "RustFS", configuras Dask o Prefect para leer directo de un Bucket (una carpeta) subido a Amazon S3.

**¿Ves lo fácil que es? Es cuestión de ir apagando contenedores e ir delegándole ese trabajo a los servicios gratuitos/administrados de Amazon.**
