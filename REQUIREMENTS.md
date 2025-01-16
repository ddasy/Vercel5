# Webhook to OKX API Forwarder Requirements

## Message Reception (Vercel Webhook)
- Webhook endpoint must handle POST requests
- Messages must be in JSON format
- Required message fields:
  - sender
  - content
  - timestamp

## Authentication Requirements
### OKX API Authentication
- Headers Required:
  - OK-ACCESS-KEY: API Key string
  - OK-ACCESS-SIGN: Base64-encoded signature
  - OK-ACCESS-TIMESTAMP: UTC timestamp (e.g., 2020-12-08T09:08:57.715Z)
  - OK-ACCESS-PASSPHRASE: API Key password
- Signature Generation:
  1. Create prehash string: timestamp + method + requestPath + body
  2. Sign using HMAC SHA256 with SecretKey
  3. Encode in Base64 format

## Message Processing
### Required Message Fields to Extract
- sender: Message originator
- content: Actual message payload
- timestamp: Message creation time

### Content Filtering Conditions
Messages should be filtered based on:
1. Message format validation (must be valid JSON)
2. Required fields presence check
3. Content type validation
4. Size limits check
5. Timestamp validation (reject if too old)

## API Integration
### OKX API Requirements
- Base URL: https://www.okx.com
- Content-Type: application/json
- Rate Limits: Follow per-endpoint limits as specified in API docs
- Error Handling:
  - Handle HTTP status codes
  - Parse error responses (code and message)
  - Implement retry mechanism for 429 (rate limit) and 5xx errors

## Security Requirements
1. Secure storage of API credentials
2. No logging of sensitive data
3. Input validation and sanitization
4. Rate limiting on webhook endpoint
5. Request signature validation
6. HTTPS only

## Logging Requirements
Log the following events:
1. Webhook reception
2. Message validation results
3. Filtering decisions
4. API call attempts and results
5. Error conditions
6. Performance metrics

## Error Handling
1. Network failures
2. API timeouts
3. Invalid message format
4. Authentication failures
5. Rate limit exceeded
6. Server errors

## Performance Requirements
1. Message processing < 1s
2. Implement retry mechanism with exponential backoff
3. Handle concurrent requests
4. Queue messages if rate limit reached

## Monitoring
1. Message reception rate
2. Processing success/failure rates
3. API response times
4. Error rates by type
5. Queue length (if implemented)
