FROM python:3.10-slim

WORKDIR /app

# Instalar Streamlit
RUN pip install --no-cache-dir streamlit pandas

# Copiar nuestra aplicación básica
COPY app.py .

# Exponer el puerto por el que se comunica Streamlit
EXPOSE 8501

# Comando por defecto para arrancar el servidor
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
