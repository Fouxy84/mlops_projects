FROM python:3.12-slim
ENV PYTHONPATH=/app
# Définition des variables d'environnement pour éviter les warnings
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 1. Installe les dépendances système minimales
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Copie et installe les dépendances Python
COPY src/training/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copie le code source
COPY src/training/main.py .
COPY src/ /app/src/

# 4. Commande de démarrage (exécution du script d'entraînement)
CMD ["uvicorn", "src.training.main:app", "--host", "0.0.0.0", "--port", "8000"]
