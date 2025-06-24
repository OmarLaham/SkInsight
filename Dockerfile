FROM python:3.12-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libpq-dev bash \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy all files
COPY . .

# Expose the application port
EXPOSE 8000

# Collect static files. Override re-write confirmation message using "--no-input" flag
RUN python manage.py collectstatic --no-input

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]

