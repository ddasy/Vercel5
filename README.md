# Webhook Message Receiver

A FastAPI-based service that receives webhook messages from Vercel, with message validation and error handling.

## Features

- Secure webhook message reception
- Message validation and signature verification
- Error handling and logging
- HTTPS endpoint at vercel5-mocha.vercel.app

## Requirements

- Python 3.12+
- Poetry for dependency management
- Environment variables (see `.env.example`)

## Installation

1. Install dependencies:
```bash
poetry install
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Configure the following environment variables:
- `WEBHOOK_SECRET`: Secret for validating webhook signatures
- `WEBHOOK_DOMAIN`: Webhook receiving domain (default: vercel5-mocha.vercel.app)

## Usage

1. Start the development server:
```bash
poetry run uvicorn app.main:app --reload
```

2. Send POST requests to `https://vercel5-mocha.vercel.app/webhook` with:
- JSON payload containing `sender`, `content`, and optional `timestamp`
- `x-vercel-signature` header for webhook validation

## API Endpoints

- `GET /healthz` - Health check endpoint
- `POST /webhook` - Webhook endpoint for receiving messages

## License

Proprietary - All rights reserved
