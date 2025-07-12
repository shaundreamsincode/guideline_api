#!/bin/bash

echo "🚀 Setting up Guideline API..."

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Django settings
DEBUG=True
SECRET_KEY=django-insecure-5#$posix)7$nqp51pvn)2==+$%_p0uzp187_nas3@4v8$xk&h%

# Database settings
DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres

# Redis settings
REDIS_URL=redis://redis:6379/0

# OpenAI settings
OPENAI_API_KEY=your_openai_api_key_here

# Celery settings
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF
    echo "⚠️  Please update .env with your actual OpenAI API key"
fi

# Build and start services
echo "Building and starting Docker services..."
docker-compose up --build -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run migrations
echo "Running database migrations..."
docker-compose exec web python manage.py migrate

echo "✅ Setup complete!"
echo ""
echo "To test the API:"
echo "1. Update .env with your OpenAI API key"
echo "2. Run: ./run_tests.sh"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f celery"
echo "  docker-compose logs -f web" 