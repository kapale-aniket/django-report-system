# Contributing to Django Report System

Thank you for your interest in contributing to the Django Report System project! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions with other contributors and maintainers.

## How to Contribute

### Reporting Bugs

1. Check existing issues to avoid duplicates
2. Create a new issue with:
   - Clear, descriptive title
   - Detailed description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and environment details
   - Relevant code snippets or error messages

### Suggesting Enhancements

1. Check existing issues to see if already suggested
2. Create an issue with:
   - Clear title
   - Detailed description of the enhancement
   - Why it would be useful
   - Example use cases

### Submitting Code

#### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd django_report_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # if available
```

#### Make Changes

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes following the code style guidelines
3. Add or update tests as needed
4. Update documentation if necessary
5. Commit with clear, concise messages:
   ```bash
   git commit -m "Brief description of changes"
   ```

#### Run Tests

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

#### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Use type hints where applicable

#### Documentation

- Update README.md if adding new features
- Add docstrings to new functions/classes
- Update API documentation if modifying endpoints
- Add inline comments for complex logic

#### Submit Pull Request

1. Push to your fork: `git push origin feature/your-feature-name`
2. Create Pull Request with:
   - Descriptive title
   - Clear description of changes
   - Reference to related issues (#123)
   - Checklist of what was tested
3. Respond to review feedback promptly

## Development Guidelines

### Project Structure

```
- Use proper app structure (Django conventions)
- Keep business logic in services/
- Keep API logic in views/serializers
- Keep models in models.py
- Use meaningful file names
```

### Git Workflow

```
main branch (stable)
├── develop branch (integration)
    ├── feature/feature-name (from develop)
    ├── bugfix/issue-name (from develop)
    └── hotfix/issue-name (from main)
```

### Commit Messages

- Use imperative mood ("Add feature" not "Added feature")
- First line: max 50 characters
- Second line: blank
- Following lines: wrap at 72 characters
- Reference issues: "Fixes #123"

### Pull Request Checklist

- [ ] Branch created from correct base branch
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Commits are clean and well-described
- [ ] No merge conflicts

## Testing Guidelines

### Writing Tests

```python
# Use descriptive test names
def test_report_creation_with_valid_data(self):
    """Test creating report with valid data."""
    
# Test one thing per test
def test_report_title_required(self):
    """Test that report title is required."""
    
# Use meaningful assertions
self.assertEqual(report.status, 'draft')
self.assertTrue(report.created_at)
self.assertRaises(ValidationError, Report.objects.create, ...)
```

### Test Coverage

Aim for at least 80% code coverage. Run:

```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # View in htmlcov/index.html
```

## API Endpoint Conventions

```
GET    /api/v1/resource/              - List resources
POST   /api/v1/resource/              - Create resource
GET    /api/v1/resource/{id}/         - Get resource
PUT    /api/v1/resource/{id}/         - Update resource
PATCH  /api/v1/resource/{id}/         - Partial update
DELETE /api/v1/resource/{id}/         - Delete resource
```

## Database Migrations

```bash
# Create migration after model changes
python manage.py makemigrations

# Create empty migration for data changes
python manage.py makemigrations --empty app_name --name migration_name

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

## Performance Considerations

- Use database query optimization (select_related, prefetch_related)
- Cache expensive operations
- Implement pagination for list endpoints
- Use appropriate database indexes
- Profile code for bottlenecks

## Documentation Standards

### Docstring Format

```python
def function_name(param1, param2):
    """
    Brief description of what function does.
    
    More detailed explanation if needed.
    
    Args:
        param1 (type): Description of param1
        param2 (type): Description of param2
        
    Returns:
        type: Description of return value
        
    Raises:
        ExceptionType: When this exception is raised
        
    Example:
        >>> result = function_name('value1', 'value2')
        >>> print(result)
    """
```

## Release Process

1. Update version number in appropriate places
2. Update CHANGELOG.md with new features/fixes
3. Create release branch
4. Tag release: `git tag -a v1.0.0 -m "Release version 1.0.0"`
5. Push tags: `git push origin --tags`
6. Create release on GitHub

## Questions?

- Check existing issues/discussions
- Review documentation
- Comment on relevant issues
- Open a new discussion

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md
- Release notes
- Project README

Thank you for contributing! 🙏
