# Testing Guide

This document provides comprehensive information about testing the Guideline API project.

## Overview

The test suite covers:
- **Model Tests**: Job model validation, constraints, and behavior
- **View Tests**: API endpoint functionality and error handling
- **Task Tests**: Celery task processing with mocked external dependencies
- **Integration Tests**: End-to-end workflow testing

## Test Structure

```
jobs/tests.py
├── JobModelTest              # Model validation and behavior
├── JobCreateViewTest         # Job creation API endpoint
├── JobDetailViewTest         # Job retrieval API endpoint
├── ProcessGuidelineTaskTest  # Celery task processing
├── JobIntegrationTest        # End-to-end workflow
└── JobModelValidationTest    # Model constraints and validation
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Basic Test Commands

Run all tests:
```bash
python manage.py test
```

Run with pytest (recommended):
```bash
python -m pytest jobs/tests.py
```

Use the test runner script:
```bash
./run_tests.sh
```

### Advanced Test Options

Run only unit tests:
```bash
./run_tests.sh --unit
```

Run only integration tests:
```bash
./run_tests.sh --integration
```

Run with coverage report:
```bash
./run_tests.sh --coverage
```

Run with verbose output:
```bash
./run_tests.sh --verbose
```

Run tests in parallel:
```bash
./run_tests.sh --parallel
```

### Pytest Commands

Run specific test class:
```bash
python -m pytest jobs/tests.py::JobModelTest -v
```

Run specific test method:
```bash
python -m pytest jobs/tests.py::JobModelTest::test_job_creation -v
```

Run tests with markers:
```bash
python -m pytest -m "not slow"  # Skip slow tests
```

## Test Categories

### 1. Model Tests (`JobModelTest`)

Tests the `Job` model functionality:
- ✅ Job creation with required fields
- ✅ UUID uniqueness for `event_id`
- ✅ Status choices validation
- ✅ String representation
- ✅ Optional fields handling

### 2. API View Tests

#### JobCreateViewTest
Tests the job creation endpoint (`POST /jobs`):
- ✅ Successful job creation
- ✅ Missing required fields validation
- ✅ Empty field validation
- ✅ Default title handling
- ✅ Invalid JSON handling
- ✅ Celery task triggering

#### JobDetailViewTest
Tests the job retrieval endpoint (`GET /jobs/<event_id>`):
- ✅ Successful job retrieval
- ✅ Non-existent job handling
- ✅ Invalid UUID handling

### 3. Celery Task Tests (`ProcessGuidelineTaskTest`)

Tests the `process_guideline` task:
- ✅ Successful guideline processing
- ✅ OpenAI API integration (mocked)
- ✅ Job not found retry logic
- ✅ Already processed job handling
- ✅ OpenAI API error handling
- ✅ Checklist parsing from various formats

### 4. Integration Tests (`JobIntegrationTest`)

Tests complete workflows:
- ✅ End-to-end job creation and retrieval
- ✅ Job status transitions
- ✅ Database consistency

### 5. Model Validation Tests (`JobModelValidationTest`)

Tests model constraints:
- ✅ Field length validation
- ✅ Required field validation
- ✅ Database constraint testing

## Mocking Strategy

### External Dependencies

The tests use mocking to isolate the code under test:

1. **OpenAI API**: Mocked using `@patch('jobs.tasks.client')`
2. **Celery Tasks**: Mocked using `@patch('jobs.views.process_guideline')`
3. **Database Transactions**: Tested with real database operations

### Example Mock Usage

```python
@patch('jobs.tasks.client')
def test_process_guideline_success(self, mock_client):
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Test summary"
    mock_client.chat.completions.create.return_value = mock_response
    
    # Test the function
    result = process_guideline(self.event_id)
    
    # Verify the mock was called
    mock_client.chat.completions.create.assert_called_once()
```

## Test Data

### Factory Boy (Optional)

For more complex test data, consider using Factory Boy:

```python
import factory
from .models import Job

class JobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Job
    
    title = factory.Faker('sentence')
    guideline_text = factory.Faker('text')
    status = 'queued'
```

## Coverage

Run coverage analysis:
```bash
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

Expected coverage targets:
- Models: 100%
- Views: 95%+
- Tasks: 90%+
- Overall: 90%+

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: python -m pytest --cov=jobs --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Best Practices

### Writing Tests

1. **Test Naming**: Use descriptive test method names
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Isolation**: Each test should be independent
4. **Mocking**: Mock external dependencies
5. **Edge Cases**: Test error conditions and edge cases

### Test Organization

1. **Group Related Tests**: Use test classes for related functionality
2. **Use setUp/tearDown**: Set up common test data
3. **Test One Thing**: Each test should verify one specific behavior
4. **Documentation**: Add docstrings to test methods

### Performance

1. **Database**: Use `@pytest.mark.django_db` for database tests
2. **Parallel Execution**: Use `pytest-xdist` for parallel test execution
3. **Slow Tests**: Mark slow tests with `@pytest.mark.slow`

## Troubleshooting

### Common Issues

1. **Database Errors**: Ensure test database is properly configured
2. **Import Errors**: Check `PYTHONPATH` and Django settings
3. **Mock Issues**: Verify mock paths match actual import paths
4. **Celery Issues**: Ensure Celery is properly configured for testing

### Debugging Tests

Run tests with debug output:
```bash
python -m pytest -s -v jobs/tests.py
```

Use pdb for debugging:
```python
import pdb; pdb.set_trace()
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain or improve coverage
4. Update this documentation if needed

## Resources

- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-django Documentation](https://pytest-django.readthedocs.io/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/) 