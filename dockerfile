# Use Python slim image
FROM python:3.13.1-slim

# Set environment variables (recommended for Django)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY /requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY salesmanPortal/ .

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose Django/Gunicorn port
EXPOSE 8000

# Run Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "salesmanPortal.wsgi:application"]
