# Django Report System

A comprehensive Django-based report management system with REST API, JWT authentication, role-based access control, AI-powered features, and advanced report workflows.

## Features

- **Report Management**: Create, view, edit, approve, and publish reports
- **User Authentication**: JWT-based authentication with role-based access control (RBAC)
- **API-First Architecture**: RESTful API with comprehensive endpoints
- **Report Versioning**: Track report history and versions
- **Certificate Management**: Auto-generate certificates from approved reports
- **AI Features**: 
  - Automated report review using GPT-4o-mini
  - OCR support for document processing
  - Q&A assistance
- **Real-time Updates**: WebSocket support for live notifications
- **Task Queue**: Celery integration for background job processing
- **Caching**: Redis caching for improved performance
- **Database**: MySQL backend with Django ORM
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation

## Tech Stack

- **Backend**: Django 6.0.4, Django REST Framework 3.15.2
- **Database**: MySQL with mysqlclient driver
- **Cache**: Redis
- **Message Queue**: Celery with Redis broker
- **Authentication**: JWT (djangorestframework-simplejwt)
- **API Docs**: DRF Spectacular
- **Frontend**: Django Templates with Bootstrap
- **PDF Processing**: ReportLab, python-docx, pdf2image
- **AI**: OpenAI GPT API integration

## Prerequisites

- Python 3.10 or higher
- MySQL Server (5.7+)
- Redis Server
- pip (Python package manager)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd django_report_system
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=project_reports_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Redis
REDIS_URL=redis://127.0.0.1:6379

# Celery
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
CELERY_TASK_ALWAYS_EAGER=True  # Set to False for production

# OpenAI (optional, for AI features)
AI_FEATURES_ENABLED=True
OPENAI_API_KEY=your_openai_api_key_here
```

### 5. Database Setup

```bash
# Create database (if not exists)
mysql -u root -p
CREATE DATABASE project_reports_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Load Sample Data (Optional)

```bash
python manage.py loaddata fixtures/sample_data.json  # if fixtures exist
```

## Running the Application

### Development Server

```bash
# Start Django development server
python manage.py runserver

# Server will run on http://127.0.0.1:8000/
```

### Background Task Worker (Celery)

In another terminal:

```bash
# Windows
celery -A config worker -l info

# Linux/macOS
celery -A config worker -l info
```

### Celery Beat Scheduler (Optional)

For scheduled tasks:

```bash
celery -A config beat -l info
```

## API Documentation

Once the server is running, access the API documentation:

- **Swagger UI**: `http://127.0.0.1:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://127.0.0.1:8000/api/schema/redoc/`
- **OpenAPI Schema**: `http://127.0.0.1:8000/api/schema/`

## Project Structure

```
django_report_system/
├── accounts/              # User authentication models
├── api/                   # API endpoints and configuration
│   ├── v1/               # API v1 endpoints
│   ├── serializers/      # DRF serializers
│   ├── filters/          # Query filters
│   └── permissions/      # Custom permissions
├── apps/                 # Django apps
│   ├── accounts/         # Account management
│   ├── reports/          # Report functionality
│   ├── messaging/        # Messaging system
│   ├── qa/              # Q&A module
│   └── dashboard/       # Dashboard
├── application/          # Application layer
│   ├── services/        # Business logic
│   ├── dtos/           # Data transfer objects
│   └── use_cases/      # Use cases
├── infrastructure/       # Infrastructure layer
│   ├── pdf/            # PDF generation
│   ├── ocr/            # OCR processing
│   ├── ai/             # AI integration
│   └── repositories/   # Database repositories
├── core/                # Core utilities
│   ├── authentication/ # Auth utilities
│   ├── permissions/    # Permission classes
│   ├── exceptions/     # Custom exceptions
│   └── middleware/     # Custom middleware
├── config/             # Django configuration
│   ├── settings.py    # Settings
│   ├── urls.py        # URL routing
│   ├── wsgi.py        # WSGI config
│   └── celery.py      # Celery config
├── templates/          # HTML templates
├── static/             # Static files (CSS, JS, images)
├── media/              # User uploaded media
├── logs/               # Application logs
├── tests/              # Test suite
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

## Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test tests.unit.test_models

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## Available Management Commands

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Check project setup
python manage.py check

# Clear cache
python manage.py cache_clear
```

## Key API Endpoints

- **Authentication**:
  - `POST /api/v1/auth/login/` - Login
  - `POST /api/v1/auth/logout/` - Logout
  - `POST /api/v1/auth/refresh/` - Refresh token
  
- **Reports**:
  - `GET /api/v1/reports/` - List reports
  - `POST /api/v1/reports/` - Create report
  - `GET /api/v1/reports/{id}/` - Get report
  - `PUT /api/v1/reports/{id}/` - Update report
  - `DELETE /api/v1/reports/{id}/` - Delete report

- **Dashboard**:
  - `GET /api/v1/dashboard/` - Get dashboard stats

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | - | Django secret key (REQUIRED) |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts |
| `DB_NAME` | `project_reports_db` | Database name |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | - | Database password |
| `DB_HOST` | `127.0.0.1` | Database host |
| `DB_PORT` | `3306` | Database port |
| `REDIS_URL` | `redis://127.0.0.1:6379` | Redis URL |
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Run Celery tasks synchronously |
| `AI_FEATURES_ENABLED` | `True` | Enable AI features |
| `OPENAI_API_KEY` | - | OpenAI API key |

## Troubleshooting

### Database Connection Issues
- Ensure MySQL is running: `mysql -u root -p`
- Check database credentials in `.env`
- Verify database exists: `SHOW DATABASES;`

### Redis Connection Issues
- Ensure Redis is running
- Check Redis URL in `.env`
- Test connection: `redis-cli ping`

### Celery Issues
- Set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` for development
- Start Celery worker separately for production
- Check Celery logs for errors

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify virtual environment is activated
- Try: `pip install --upgrade pip`

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions, please create an issue in the repository or contact the development team.

## Authors

- College Final Year Project Team

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

---

**Last Updated**: June 2026
**Version**: 1.0.0
