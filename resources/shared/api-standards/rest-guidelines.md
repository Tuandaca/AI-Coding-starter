# REST API Guidelines

## Design Principles

- Resource-oriented URLs (nouns, not verbs)
- Consistent pluralization (`/users`, not `/user`)
- Hierarchical relationships (`/users/{id}/posts`)
- Version in URL (`/api/v1/`) or header

## HTTP Methods

| Method | Purpose | Idempotent |
|--------|---------|------------|
| GET | Retrieve resource | Yes |
| POST | Create resource | No |
| PUT | Replace resource | Yes |
| PATCH | Partial update | No |
| DELETE | Remove resource | Yes |

## Status Codes

### Success
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE

### Client Errors
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing/invalid auth
- `403 Forbidden` - Authenticated but not allowed
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Resource conflict
- `422 Unprocessable Entity` - Validation failed
- `429 Too Many Requests` - Rate limited

### Server Errors
- `500 Internal Server Error` - Unexpected error
- `503 Service Unavailable` - Temporary outage

## Request/Response Format

### Content-Type
- Request: `application/json`
- Response: `application/json`

### Error Response Structure
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": [
      { "field": "email", "issue": "Invalid format" }
    ]
  }
}
```

### Pagination
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

## Filtering, Sorting, Searching
- Filter: `?status=active&category=tech`
- Sort: `?sort=-created_at,title`
- Search: `?q=search+term`

## Security
- Always use HTTPS
- Rate limiting on all endpoints
- Input validation and sanitization
- CORS configured appropriately
- Authentication via Bearer tokens (JWT)
