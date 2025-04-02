# Authentication System

## Overview

The Parliament Video Clip Manager uses a JWT-based authentication system with role-based access control (RBAC). Users are assigned one of three roles: ADMIN, MP, or STAFF, each with different permissions and access levels.

## User Roles

- **ADMIN**: Full system access, can manage users and system settings
- **MP**: Members of Parliament, can create and manage their own clips
- **STAFF**: Staff members, can assist with clip management and social media

## Authentication Flow

1. **Login**
   ```http
   POST /api/v1/auth/login
   Content-Type: application/x-www-form-urlencoded

   username=user@parliament.uk&password=userpass
   ```
   Returns a JWT token for subsequent requests.

2. **Protected Endpoints**
   - Include the JWT token in the Authorization header:
   ```http
   Authorization: Bearer <token>
   ```

## API Endpoints

### Authentication

- `POST /api/v1/auth/login`: User login
- `POST /api/v1/auth/register`: Register new user (ADMIN only)
- `GET /api/v1/auth/me`: Get current user info
- `PUT /api/v1/auth/me`: Update current user info
- `GET /api/v1/auth/users`: List all users (ADMIN only)

### Response Format

```json
{
    "access_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
}
```

## Security Features

1. **Password Hashing**
   - Uses bcrypt for secure password hashing
   - Configurable work factor for hash strength

2. **JWT Configuration**
   - Configurable token expiration
   - Signed with a secure secret key
   - Role information embedded in token

3. **Role Validation**
   - Strict role enum validation (ADMIN, MP, STAFF)
   - Role-based endpoint access control
   - Automatic role verification on protected routes

## Testing

The authentication system includes comprehensive test coverage:

1. **Test Setup**
   - Uses a separate test database
   - Automatic database cleanup between tests
   - Helper functions for creating test users

2. **Test Cases**
   - Login success/failure scenarios
   - Token validation
   - Role-based access control
   - User registration
   - Profile updates

3. **Running Tests**
   ```bash
   # Run auth tests
   pytest tests/test_auth_endpoints.py -v
   ```

## Configuration

Key settings in `.env`:
```env
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Error Handling

Common error responses:
- 401: Invalid credentials
- 403: Insufficient permissions
- 422: Validation error (e.g., invalid role)
