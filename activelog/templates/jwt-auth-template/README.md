# jwt-auth-template

JWT-based authentication service with login and token validation

## Usage

```bash
./create-auth-service.sh --template=jwt-auth-template --port=8001
```

## Integration Guide

1. Set SECRET_KEY environment variable 2. Implement user authentication logic 3. Use verify_token dependency in protected routes

## Dependencies

- fastapi
- pyjwt
- python-multipart