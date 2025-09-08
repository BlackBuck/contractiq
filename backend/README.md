# Backend - Running tests in Docker

This project includes a GitHub Actions workflow that builds the backend Docker image and runs the test suite inside the container. Use the same commands locally to reproduce CI behavior.

Run locally (PowerShell):

```powershell
cd backend
# build image
docker build -t contract-backend:local .

# run tests inside container (mount repo to collect results)
docker run --rm -v "${PWD}:/work" -w /work/backend contract-backend:local bash -lc "pytest -q --junitxml=/work/backend/test-results.xml"

# test-results.xml will be created in backend/ if you want CI parity
```

The CI workflow located at `.github/workflows/ci.yml` does the same on push/pull requests to `main`.

# Backend for Contract Intelligence Parser

This is the FastAPI backend for the contract intelligence system.

## Structure

- `app/` - FastAPI app, routers, models, and extraction logic
- `tests/` - Unit tests
- `Dockerfile` - Docker build for backend
- `requirements.txt` - Python dependencies

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run: `uvicorn app.main:app --reload`

## Features

- Async contract upload and processing
- MongoDB integration
- REST API endpoints as per requirements
- Placeholder extraction and scoring logic
