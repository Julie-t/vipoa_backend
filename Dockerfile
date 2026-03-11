# Base image
FROM python:3.11-slim

# Prevent Python from writing pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Railway expects
EXPOSE 8080

# CMD: run migrations, create superuser, start Gunicorn
CMD ["sh", "-c", "\
python manage.py migrate && \
python manage.py shell -c \"from django.contrib.auth import get_user_model; \
import os; \
User=get_user_model(); \
username=os.environ.get('DJANGO_SUPERUSER_USERNAME'); \
email=os.environ.get('DJANGO_SUPERUSER_EMAIL'); \
password=os.environ.get('DJANGO_SUPERUSER_PASSWORD'); \
if username and password and not User.objects.filter(username=username).exists(): \
    User.objects.create_superuser(username, email, password)\" && \
gunicorn vipoa_backend.wsgi:application --bind 0.0.0.0:$PORT \
"]