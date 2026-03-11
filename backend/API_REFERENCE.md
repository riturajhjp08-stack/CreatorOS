# CreatorOS API Reference

Complete API documentation for all backend endpoints.

## Table of Contents
1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Platforms](#platforms)
4. [Analytics](#analytics)
5. [Error Handling](#error-handling)

---

## Authentication

### Register User
**POST** `/api/auth/register`

Register a new user account.

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePassword123!",
  "referral_code": ""
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "John Doe",
    "email": "john@example.com",
    "credits": 100,
    "premium": false,
    "avatar_url": null,
    "bio": null,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors:**
- `400 Bad Request`: Missing required fields
- `409 Conflict`: Email already registered

---

### Login
**POST** `/api/auth/login`

Authenticate user with email and password.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "John Doe",
    "email": "john@example.com",
    "credits": 100,
    "premium": false
  }
}
```

**Errors:**
- `400 Bad Request`: Missing credentials
- `401 Unauthorized`: Invalid email/password

---

### Verify Token
**GET** `/api/auth/verify-token`

Verify JWT token validity.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "valid": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `401 Unauthorized`: Invalid/expired token
- `403 Forbidden`: Missing token

---

### Logout
**POST** `/api/auth/logout`

Invalidate current session.

**Headers:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

---

### Google OAuth Login
**POST** `/api/auth/google/login`

Initiate Google OAuth flow.

**Response (200 OK):**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

---

### Google OAuth Callback
**GET** `/api/auth/google/callback`

Handle Google OAuth callback.

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: CSRF token

**Response (302 Redirect):**
Redirects to frontend with JWT token in URL fragment.

---

### TikTok OAuth Login
**POST** `/api/auth/tiktok/login`

Initiate TikTok OAuth flow.

**Response (200 OK):**
```json
{
  "auth_url": "https://www.tiktok.com/v1/oauth/authorize?client_id=..."
}
```

---

### TikTok OAuth Callback
**GET** `/api/auth/tiktok/callback`

Handle TikTok OAuth callback.

**Query Parameters:**
- `code`: Authorization code from TikTok
- `state`: CSRF token

**Response (302 Redirect):**
Redirects to frontend with JWT token in URL fragment.

---

## User Management

### Get Profile
**GET** `/api/user/profile`

Get current user's profile.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "John Doe",
  "email": "john@example.com",
  "credits": 100,
  "premium": false,
  "bio": "Content creator",
  "avatar_url": "https://example.com/avatar.jpg",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-16T14:20:00Z",
  "notification_email": true,
  "notification_browser": true
}
```

---

### Update Profile
**PUT** `/api/user/profile`

Update user profile information.

**Headers:**
```
Authorization: Bearer [token]
Content-Type: application/json
```

**Request:**
```json
{
  "name": "Jane Doe",
  "bio": "Updated bio",
  "avatar_url": "https://example.com/new-avatar.jpg",
  "notification_email": true,
  "notification_browser": false
}
```

**Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Jane Doe",
    "bio": "Updated bio",
    "avatar_url": "https://example.com/new-avatar.jpg"
  }
}
```

---

### Change Password
**POST** `/api/user/password`

Change user password.

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "old_password": "CurrentPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully"
}
```

**Errors:**
- `400 Bad Request`: Invalid old password
- `400 Bad Request`: Password doesn't meet requirements

---

### Get Credits
**GET** `/api/user/credits`

Get user's credit balance.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "credits": 100,
  "premium": false,
  "total_spent": 0,
  "reset_date": "2024-02-15T00:00:00Z"
}
```

---

### Use Credits
**POST** `/api/user/credits/use`

Deduct credits for platform usage.

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "amount": 10,
  "reason": "Platform analytics"
}
```

**Response (200 OK):**
```json
{
  "remaining_credits": 90,
  "message": "10 credits used successfully"
}
```

---

### Enable 2FA
**POST** `/api/user/2fa/enable`

Enable two-factor authentication.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "message": "2FA enabled",
  "secret": "JBSWY3DPEBLW64TQMQ"
}
```

---

### Disable 2FA
**POST** `/api/user/2fa/disable`

Disable two-factor authentication.

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "password": "CurrentPassword123!"
}
```

**Response (200 OK):**
```json
{
  "message": "2FA disabled"
}
```

---

### Get OAuth Accounts
**GET** `/api/user/oauth-accounts`

List all connected OAuth providers.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "oauth_accounts": [
    {
      "provider": "google",
      "email": "john@gmail.com",
      "connected_at": "2024-01-15T10:30:00Z"
    },
    {
      "provider": "tiktok",
      "email": "john_creator",
      "connected_at": "2024-01-16T14:20:00Z"
    }
  ]
}
```

---

### Delete Account
**POST** `/api/user/delete`

Permanently delete user account and all data.

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "password": "CurrentPassword123!"
}
```

**Response (200 OK):**
```json
{
  "message": "Account deleted successfully"
}
```

---

## Platforms

### Get Connected Platforms
**GET** `/api/platforms/connected`

List all user's connected platforms.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "platforms": [
    {
      "id": "platform-001",
      "platform": "youtube",
      "platform_display_name": "YouTube",
      "platform_user_id": "UC1234567890",
      "platform_username": "john_creator",
      "profile_url": "https://youtube.com/c/john_creator",
      "avatar_url": "https://example.com/avatar.jpg",
      "connected_at": "2024-01-15T10:30:00Z",
      "is_active": true
    }
  ]
}
```

---

### YouTube Auth
**POST** `/api/platforms/youtube/auth`

Initiate YouTube OAuth flow.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

---

### YouTube Callback
**GET** `/api/platforms/youtube/callback`

Handle YouTube OAuth callback.

**Query Parameters:**
- `code`: Authorization code
- `state`: CSRF token

**Response (302 Redirect):**
Redirects to frontend with success message.

---

### Connect Platform
**POST** `/api/platforms/connect`

Manually connect a platform (without OAuth).

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "platform": "instagram",
  "platform_user_id": "123456789",
  "platform_username": "john_creator",
  "access_token": "instagram_access_token"
}
```

**Response (201 Created):**
```json
{
  "message": "Platform connected successfully",
  "platform": {
    "id": "platform-002",
    "platform": "instagram",
    "platform_username": "john_creator"
  }
}
```

---

### Disconnect Platform
**POST** `/api/platforms/disconnect`

Disconnect a platform.

**Headers:**
```
Authorization: Bearer [token]
```

**Request:**
```json
{
  "platform_id": "platform-001"
}
```

**Response (200 OK):**
```json
{
  "message": "Platform disconnected successfully"
}
```

---

### Sync All Platforms
**POST** `/api/platforms/sync-all`

Manually refresh analytics for all connected platforms.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "message": "Sync started",
  "synced_platforms": ["youtube", "tiktok"],
  "failed": [],
  "timestamp": "2024-01-16T15:30:00Z"
}
```

---

## Analytics

### Dashboard Analytics
**GET** `/api/analytics/dashboard`

Get aggregated analytics across all platforms.

**Headers:**
```
Authorization: Bearer [token]
```

**Query Parameters:**
- `days`: Number of days history (default: 30)

**Response (200 OK):**
```json
{
  "summary": {
    "total_views": 1500000,
    "total_followers": 50000,
    "total_engagement": 75000,
    "total_posts": 150
  },
  "platforms": [
    {
      "platform": "youtube",
      "views": 1000000,
      "followers": 30000,
      "engagement": 45000,
      "posts": 100
    },
    {
      "platform": "tiktok",
      "views": 500000,
      "followers": 20000,
      "engagement": 30000,
      "posts": 50
    }
  ],
  "trend": "up"
}
```

---

### Platform Analytics
**GET** `/api/analytics/platform/{platform}`

Get analytics for specific platform.

**Headers:**
```
Authorization: Bearer [token]
```

**Query Parameters:**
- `days`: Number of days history (default: 30)

**Response (200 OK):**
```json
{
  "platform": "youtube",
  "data": [
    {
      "date": "2024-01-15",
      "views": 5000,
      "followers": 1000,
      "engagement": 500,
      "posts": 1
    },
    {
      "date": "2024-01-16",
      "views": 6000,
      "followers": 1050,
      "engagement": 630,
      "posts": 2
    }
  ]
}
```

---

### Latest Platform Analytics
**GET** `/api/analytics/platform/{platform}/latest`

Get most recent metrics for platform.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "platform": "youtube",
  "data": {
    "date": "2024-01-16",
    "views": 1000000,
    "followers": 30000,
    "engagement": 45000,
    "posts": 100
  }
}
```

---

### Trending Platforms
**GET** `/api/analytics/trending`

Get growth rates for all platforms.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "trending": [
    {
      "platform": "tiktok",
      "view_growth": 12.5,
      "follower_growth": 8.2,
      "engagement_growth": 15.3
    },
    {
      "platform": "youtube",
      "view_growth": 5.2,
      "follower_growth": 3.1,
      "engagement_growth": 4.8
    }
  ]
}
```

---

### Compare Platforms
**GET** `/api/analytics/comparison`

Get side-by-side platform comparison.

**Headers:**
```
Authorization: Bearer [token]
```

**Response (200 OK):**
```json
{
  "comparison": {
    "youtube": {
      "views": 1000000,
      "followers": 30000,
      "engagement": 45000,
      "posts": 100,
      "rank": 1
    },
    "tiktok": {
      "views": 500000,
      "followers": 20000,
      "engagement": 30000,
      "posts": 50,
      "rank": 2
    }
  }
}
```

---

### Export Analytics
**GET** `/api/analytics/export`

Export analytics as CSV.

**Headers:**
```
Authorization: Bearer [token]
```

**Query Parameters:**
- `format`: "csv" or "json" (default: csv)
- `days`: Number of days (default: 30)

**Response (200 OK):**
```
Content-Type: text/csv

date,platform,views,followers,engagement,posts
2024-01-15,youtube,5000,1000,500,1
2024-01-15,tiktok,3000,800,300,2
...
```

---

## Error Handling

All errors return appropriate HTTP status codes with error details.

### Error Response Format
```json
{
  "error": "Error message",
  "status": 400,
  "details": "Additional error details"
}
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 500 | Server Error - Unexpected error |

---

## Authentication

All protected endpoints require JWT token in Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token is valid for 30 days from issue date.

---

## Rate Limiting

Not implemented in current version. Recommended to add:
- 100 requests per minute per user
- 1000 requests per hour per user

---

## Pagination

Not implemented in current version. For future compatibility:

```
GET /api/endpoint?page=1&limit=20
```

Response includes:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

---

## Testing API Endpoints

Use the provided test script:
```bash
python3 test-backend.py
```

This will:
- ✓ Verify backend is running
- ✓ Test database connectivity
- ✓ Test user registration
- ✓ Test authentication flow
- ✓ Test profile operations
- ✓ Test platform connections
- ✓ Test analytics retrieval

---

## Example curl Commands

### Register User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### Get Profile
```bash
curl -X GET http://localhost:5000/api/user/profile \
  -H "Authorization: Bearer your_token_here"
```

### Get Dashboard Analytics
```bash
curl -X GET "http://localhost:5000/api/analytics/dashboard?days=30" \
  -H "Authorization: Bearer your_token_here"
```

---

Last Updated: 2024-01-16
API Version: 1.0
