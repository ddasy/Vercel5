# Webhook to OKX API Forwarder

A FastAPI-based service that receives webhook messages from Vercel and forwards them to the OKX API with proper authentication, filtering, and error handling.

## Features

- Webhook message reception and validation
- Message content filtering and sanitization
- Secure OKX API integration with authentication
- Comprehensive error handling and retry mechanism
- Detailed logging and monitoring
- Test coverage at 84%

## Requirements

- Python 3.12+
- Poetry for dependency management
- Environment variables (see `.env.example`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ddasy/Vercel.git
cd Vercel
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

4. Configure the following environment variables:
- `WEBHOOK_SECRET`: Secret for validating webhook signatures
- `OKX_API_KEY`: Your OKX API key
- `OKX_SECRET_KEY`: Your OKX API secret key
- `OKX_PASSPHRASE`: Your OKX API passphrase
- `OKX_API_URL`: OKX API URL (defaults to production)

## Usage

1. Start the server:
```bash
poetry run uvicorn app.main:app --reload
```

2. Send POST requests to `/webhook` endpoint with:
- JSON payload containing `sender`, `content`, and optional `timestamp`
- `x-vercel-signature` header for webhook validation

## Testing

Run tests with coverage:
```bash
poetry run pytest tests/ -v --cov=app
```

## Version

Current version: 1.0.4

## License

Proprietary - All rights reserved
