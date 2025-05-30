# Imacall API Documentation (Version 0.1.0)

This document describes the API endpoints for the Imacall application, based on the OpenAPI 3.1 specification available at `/api/v1/openapi.json`.

**Base URL:** `https://imacall-backend-production.up.railway.app/api/v1`  
**Alternative Base URL:** `https://imacall-backend.onrender.com/api/v1` (if specified)

## 🚀 Current Status & Updates

**✅ Fully Operational (Updated January 2025):**
- Complete character management system with V3 personality fields
- Multi-provider AI integration with fallback support
- Working AI providers: Gemini 2.0 Flash, DeepSeek Chat V3, Qwen3 235B, Gemma3 27B
- User authentication and admin management
- Real-time conversation system
- Database migrations completed with AI provider configuration

**🔧 Recent Updates:**
- **AI Provider System:** Upgraded to support multiple OpenRouter models
- **Gemini Integration:** Updated to new `google-genai` package with Gemini 2.0 Flash
- **Character Fallback Responses:** Added fallback system for AI failures
- **Enhanced Character Fields:** Added comprehensive personality system (V3)
- **Database Stability:** Resolved migration conflicts and ensured data integrity

**⚡ AI Provider Status:**
- **Recommended:** `deepseek-chat` (Most reliable OpenRouter model)
- **Default:** `gemini` (Google Gemini 2.0 Flash)
- **Also Working:** `qwen3`, `gemma3`
- **Available:** All OpenRouter free models via single API key

---

## Authentication (`/login`)

### Login for Access Token

*   **Endpoint:** `POST /login/access-token`
*   **Description:** OAuth2 compatible token login. Obtain an access token for subsequent authenticated requests.
*   **Request Body:** `application/x-www-form-urlencoded`
    *   `grant_type`: `string` (Must be "password")
    *   `username`: `string` (User's email) *Required*
    *   `password`: `string` *Required*
    *   `scope`: `string` (Optional)
    *   `client_id`: `string` (Optional)
    *   `client_secret`: `string` (Optional)
*   **Responses:**
    *   `200 OK`: Successful login.
        ```json
        {
          "access_token": "string",
          "token_type": "bearer"
        }
        ```
    *   `422 Unprocessable Entity`: Validation error (e.g., missing fields).
        ```json
        {
          "detail": [
            { "loc": ["body", "username"], "msg": "field required", "type": "value_error.missing" }
          ]
        }
        ```
    *   `400/401 Bad Request/Unauthorized`: Incorrect email or password (Actual status code may depend on specific implementation, often 400 or 401).

### Test Access Token

*   **Endpoint:** `POST /login/test-token`
*   **Description:** Test if the provided access token in the `Authorization: Bearer <token>` header is valid. Returns the user associated with the token.
*   **Authentication:** Requires `Authorization: Bearer <token>` header.
*   **Responses:**
    *   `200 OK`: Token is valid. Returns user details.
        ```json
        {
          "email": "user@example.com",
          "is_active": true,
          "is_superuser": false,
          "full_name": "string",
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
        ```
    *   `401 Unauthorized`: Invalid or expired token.

### Request Password Recovery

*   **Endpoint:** `POST /password-recovery/{email}`
*   **Description:** Initiates the password recovery process for the given email address. Typically sends a recovery email.
*   **Parameters:**
    *   `email`: `string` (Path parameter) *Required*
*   **Responses:**
    *   `200 OK`: Password recovery initiated (e.g., email sent). The response body seems generic in the spec, might just indicate success.
        ```json
        {
          "msg": "Password recovery email sent" // Example adjusted for clarity
        }
        ```
    *   `404 Not Found`: User with the specified email does not exist.
    *   `422 Unprocessable Entity`: Invalid email format.

### Reset Password

*   **Endpoint:** `POST /reset-password/`
*   **Description:** Resets the user's password using a valid token obtained from the password recovery process.
*   **Request Body:** `application/json`
    ```json
    {
      "token": "string", // The recovery token received by the user
      "new_password": "string" // New password (min 8 characters)
    }
    ```
*   **Responses:**
    *   `200 OK`: Password successfully reset. The response body seems generic in the spec.
        ```json
        {
          "msg": "Password updated successfully" // Example adjusted for clarity
        }
        ```
    *   `400 Bad Request`: Invalid or expired token, or other issues.
    *   `422 Unprocessable Entity`: Validation error (e.g., password too short).

### Get Password Recovery HTML Content (Utility)

*   **Endpoint:** `POST /password-recovery-html-content/{email}`
*   **Description:** Utility endpoint to get the HTML content of the password recovery email (likely for testing/preview).
*   **Parameters:**
    *   `email`: `string` (Path parameter) *Required*
*   **Responses:**
    *   `200 OK`: Returns HTML content.
        *   **Media Type:** `text/html`
    *   `422 Unprocessable Entity`: Invalid email format.

---

## Users (`/users`)

### List Users (Admin)

*   **Endpoint:** `GET /users/`
*   **Description:** Retrieve a list of users. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0) - Number of users to skip.
    *   `limit`: `integer` (Query, Default: 100) - Maximum number of users to return.
*   **Responses:**
    *   `200 OK`: List of users.
        ```json
        {
          "data": [
            {
              "email": "user@example.com",
              "is_active": true,
              "is_superuser": false,
              "full_name": "string",
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
          ],
          "count": 0 // Total number of users matching the query
        }
        ```
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `422 Unprocessable Entity`: Invalid query parameters.

### Create User (Admin)

*   **Endpoint:** `POST /users/`
*   **Description:** Create a new user. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Request Body:** `application/json` (`UserCreate` schema)
    ```json
    {
      "email": "user@example.com", // Required
      "password": "stringst",       // Required (min 8 chars)
      "is_active": true,          // Optional, default: true
      "is_superuser": false,        // Optional, default: false
      "full_name": "string"         // Optional
    }
    ```
*   **Responses:**
    *   `200 OK`: User created successfully. Returns the created user details (`UserPublic` schema).
        ```json
        {
          "email": "user@example.com",
          "is_active": true,
          "is_superuser": false,
          "full_name": "string",
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
        ```
    *   `400 Bad Request`: Email already registered.
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `422 Unprocessable Entity`: Validation error.

### Register User (Public)

*   **Endpoint:** `POST /users/signup`
*   **Description:** Create a new user account. Does not require authentication.
*   **Request Body:** `application/json` (`UserRegister` schema)
    ```json
    {
      "email": "user@example.com", // Required
      "password": "stringst",       // Required (min 8 chars)
      "full_name": "string"         // Optional
    }
    ```
*   **Responses:**
    *   `200 OK`: User registered successfully. Returns the created user details (`UserPublic` schema).
        ```json
        {
          "email": "user@example.com",
          "is_active": true, // Usually true by default on registration
          "is_superuser": false,
          "full_name": "string",
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
        ```
    *   `400 Bad Request`: Email already registered.
    *   `422 Unprocessable Entity`: Validation error (e.g., invalid email, password too short).

### Get Current User

*   **Endpoint:** `GET /users/me`
*   **Description:** Get details for the currently authenticated user.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Responses:**
    *   `200 OK`: Returns current user details (`UserPublic` schema).
        ```json
        {
          "email": "user@example.com",
          "is_active": true,
          "is_superuser": false,
          "full_name": "string",
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
        ```
    *   `401 Unauthorized`: Not authenticated.

### Update Current User

*   **Endpoint:** `PATCH /users/me`
*   **Description:** Update details (full name, email) for the currently authenticated user.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Request Body:** `application/json` (`UserUpdateMe` schema)
    ```json
    {
      "full_name": "string", // Optional
      "email": "user@example.com" // Optional
    }
    ```
*   **Responses:**
    *   `200 OK`: User updated successfully. Returns updated user details (`UserPublic` schema).
    *   `400 Bad Request`: Email already taken by another user.
    *   `401 Unauthorized`: Not authenticated.
    *   `422 Unprocessable Entity`: Validation error.

### Update Current User's Password

*   **Endpoint:** `PATCH /users/me/password`
*   **Description:** Update the password for the currently authenticated user.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Request Body:** `application/json` (`UpdatePassword` schema)
    ```json
    {
      "current_password": "string", // Required (min 8 chars)
      "new_password": "string"      // Required (min 8 chars)
    }
    ```
*   **Responses:**
    *   `200 OK`: Password updated successfully. Response body seems generic.
        ```json
        {
            "msg": "Password updated successfully" // Example adjusted
        }
        ```
    *   `400 Bad Request`: Incorrect current password.
    *   `401 Unauthorized`: Not authenticated.
    *   `422 Unprocessable Entity`: Validation error (e.g., new password too short).

### Delete Current User

*   **Endpoint:** `DELETE /users/me`
*   **Description:** Delete the currently authenticated user's account.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Responses:**
    *   `200 OK`: User deleted successfully. Response body seems generic.
        ```json
        {
            "msg": "User deleted successfully" // Example adjusted
        }
        ```
    *   `401 Unauthorized`: Not authenticated.

### Get User by ID (Admin)

*   **Endpoint:** `GET /users/{user_id}`
*   **Description:** Get details for a specific user by their ID. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `user_id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: Returns user details (`UserPublic` schema).
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `404 Not Found`: User with the specified ID not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

### Update User by ID (Admin)

*   **Endpoint:** `PATCH /users/{user_id}`
*   **Description:** Update details for a specific user by their ID. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `user_id`: `string` (Path parameter, UUID format) *Required*
*   **Request Body:** `application/json` (`UserUpdate` schema - Allows updating more fields than `/users/me`)
    ```json
    {
      "email": "user@example.com", // Optional
      "password": "newpassword",    // Optional (min 8 chars)
      "is_active": true,          // Optional
      "is_superuser": false,        // Optional
      "full_name": "string"         // Optional
    }
    ```
*   **Responses:**
    *   `200 OK`: User updated successfully. Returns updated user details (`UserPublic` schema).
    *   `400 Bad Request`: Email already taken.
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `404 Not Found`: User not found.
    *   `422 Unprocessable Entity`: Validation error.

### Delete User by ID (Admin)

*   **Endpoint:** `DELETE /users/{user_id}`
*   **Description:** Delete a specific user by their ID. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `user_id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: User deleted successfully. Response body seems generic.
        ```json
        {
            "msg": "User deleted successfully" // Example adjusted
        }
        ```
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `404 Not Found`: User not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

---

## Characters

**Character Schema (Complete)**

```json
{
  "id": "uuid",
  "name": "string (max 100)", // Required
  "description": "string (text, optional)",
  "image_url": "string (url, optional)",
  "greeting_message": "string (text, optional)",
  "scenario": "string (text, optional)",
  "category": "string (optional)",
  "language": "string (optional)",
  "tags": ["string", "..."] | "string" (optional), // Can be array or comma-separated string
  "voice_id": "string (optional)", // For TTS integration
  // V3 Personality Fields
  "personality_traits": "string (text, optional)", // e.g., "Curious, Witty, Cautious"
  "writing_style": "string (text, optional)", // e.g., "Formal, Concise, Uses emojis"
  "background": "string (text, optional)", // Character's history
  "knowledge_scope": "string (text, optional)", // What the character knows/doesn't know
  "quirks": "string (text, optional)", // Unique habits or behaviors
  "emotional_range": "string (text, optional)", // How the character expresses emotions
  "popularity_score": "integer (default 0)",
  "status": "string (pending | approved | rejected)",
  "is_public": "boolean (default true)",
  "is_featured": "boolean (default false)",
  "creator_id": "uuid",
  "created_at": "datetime",
  "updated_at": "datetime",
  "admin_feedback": "string (text, optional)", // Only visible to admins
  "fallback_response": "string (text, optional)" // Only visible to admins, used when AI fails
}
```

**Character Field Details:**

- **Core Fields**: `name` (required), `description`, `image_url`, `greeting_message`
- **Categorization**: `category`, `language`, `tags`, `voice_id`
- **Scenario**: `scenario` - Context/setting for interactions
- **Personality System** (V3):
  - `personality_traits` - Core personality characteristics
  - `writing_style` - How the character communicates
  - `background` - Character's history and context
  - `knowledge_scope` - What the character knows about
  - `quirks` - Unique behaviors and habits
  - `emotional_range` - How emotions are expressed
- **Admin Fields**: `status`, `is_public`, `is_featured`, `admin_feedback`, `fallback_response`
- **System Fields**: `id`, `creator_id`, `created_at`, `updated_at`, `popularity_score`

**Notes:**
- `tags` field supports both JSON array format `["tag1", "tag2"]` and comma-separated string `"tag1, tag2"`
- `admin_feedback` and `fallback_response` are excluded from public API responses
- All text fields (`description`, `greeting_message`, `scenario`, personality fields) use TEXT columns for unlimited length
- `fallback_response` is used when AI providers fail to generate responses

**Endpoints:**

1.  **`GET /characters/` (Public)**
    *   **Description:** Retrieves a list of publicly available and approved characters.
    *   **Authentication:** Not required.
    *   **Query Parameters:** `skip` (int, default 0), `limit` (int, default 100).
    *   **Response:** `CharactersPublic` (contains a list of `CharacterPublic` objects and total count).

2.  **`GET /characters/my-submissions`**
    *   **Description:** Retrieves characters submitted by the currently authenticated user (any status).
    *   **Authentication:** Required.
    *   **Query Parameters:** `skip` (int, default 0), `limit` (int, default 100).
    *   **Response:** `CharactersPublic`.

3.  **`GET /characters/{id}` (Public)**
    *   **Description:** Retrieves a specific approved character by its ID.
    *   **Authentication:** Not required.
    *   **Response:** `CharacterPublic` or 404 if not found or not approved.

4.  **`POST /characters/submit`**
    *   **Description:** Submits a new character for review. Status defaults to `pending`.
    *   **Authentication:** Required.
    *   **Request Body:** `CharacterCreate` (requires `name`, other fields are optional, text fields have no strict length limit).
    *   **Response:** `CharacterPublic` (the created character data).

---

## Admin - Characters (`/admin/characters`)

*Requires superuser privileges for all endpoints.*

### List All Characters (Admin)

*   **Endpoint:** `GET /admin/characters/`
*   **Description:** Retrieve all characters across all users and statuses.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0)
    *   `limit`: `integer` (Query, Default: 100)
    *   `status`: `string` (Query, Optional) - Filter by status (`pending`, `approved`, `rejected`).
*   **Responses:**
    *   `200 OK`: List of all characters (`CharactersPublic` schema).
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `422 Unprocessable Entity`: Invalid query parameters.

### List Pending Characters (Admin)

*   **Endpoint:** `GET /admin/characters/pending`
*   **Description:** Retrieve all characters with `pending` status. (Shortcut for `GET /admin/characters/?status=pending`)
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0)
    *   `limit`: `integer` (Query, Default: 100)
*   **Responses:**
    *   `200 OK`: List of pending characters (`CharactersPublic` schema).
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `422 Unprocessable Entity`.

### Approve Character (Admin)

*   **Endpoint:** `PATCH /admin/characters/{id}/approve`
*   **Description:** Change a character's status from `pending` (or `rejected`) to `approved`.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: Character approved. Returns updated character details (`CharacterPublic` schema) with `approved` status.
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `404 Not Found`: Character not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

### Reject Character (Admin)

*   **Endpoint:** `PATCH /admin/characters/{id}/reject`
*   **Description:** Change a character's status from `pending` to `rejected`. *(Note: API might allow rejecting an already approved character too)*. Can optionally include feedback.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Request Body (Optional):** `application/json`
    ```json
    {
        "adminFeedback": "Reason for rejection" // Optional feedback
    }
    ```
*   **Responses:**
    *   `200 OK`: Character rejected. Returns updated character details (`CharacterPublic` schema) with `rejected` status (and potentially feedback).
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `404 Not Found`: Character not found.
    *   `422 Unprocessable Entity`: Invalid UUID format or validation error in body.

### Get Character (Admin)

*   **Endpoint:** `GET /admin/characters/{id}`
*   **Description:** Get detailed information about a specific character by ID, including admin-only fields like `admin_feedback` and `fallback_response`. Returns character regardless of status.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: Character details with all fields (`CharacterAdmin` schema).
        ```json
        {
          "id": "uuid",
          "name": "Character Name",
          "description": "...",
          "image_url": "...",
          "greeting_message": "...",
          "scenario": "...",
          "category": "...",
          "language": "...",
          "tags": ["tag1", "tag2"],
          "voice_id": "...",
          "personality_traits": "...",
          "writing_style": "...",
          "background": "...",
          "knowledge_scope": "...",
          "quirks": "...",
          "emotional_range": "...",
          "popularity_score": 100,
          "status": "pending|approved|rejected",
          "is_public": true,
          "is_featured": false,
          "creator_id": "uuid",
          "created_at": "2025-01-01T12:00:00Z",
          "updated_at": "2025-01-01T12:00:00Z",
          "admin_feedback": "Optional admin feedback",
          "fallback_response": "Fallback message for AI failures"
        }
        ```
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `404 Not Found`: Character not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

### Update Character (Admin)

*   **Endpoint:** `PUT /admin/characters/{id}`
*   **Description:** Update any field of a character, including status. This is the main endpoint for admin edits. *Note: Uses PUT, implying a full replacement of editable fields based on the request body, or partial update if backend logic allows.*
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Request Body:** `application/json` (`CharacterUpdateAdmin` schema) - Include only fields to be updated.
    ```json
    {
      "name": "Updated Name", // Optional
      "description": "Updated description", // Optional
      "image_url": "...", // Optional
      "greeting_message": "...", // Optional
      "status": "approved", // Optional (e.g., "pending", "approved", "rejected")
      "category": "Fantasy", // Optional
      "tags": ["new", "tags"], // Optional
      "isPublic": true, // Optional
      "adminFeedback": null // Optional (e.g., to clear feedback)
      // ... other fields from CharacterUpdateAdmin schema
    }
    ```
*   **Responses:**
    *   `200 OK`: Character updated successfully. Returns updated character details (`CharacterPublic` schema).
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `404 Not Found`: Character not found.
    *   `422 Unprocessable Entity`: Validation error.

### Delete Character (Admin)

*   **Endpoint:** `DELETE /admin/characters/{id}`
*   **Description:** Permanently delete a character.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: Character deleted successfully. Response body seems generic.
        ```json
        {
            "msg": "Character deleted successfully" // Example adjusted
        }
        ```
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `404 Not Found`: Character not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

---

## Conversations (`/conversations`)

### Start Conversation

*   **Endpoint:** `POST /conversations/`
*   **Description:** Initiate a new chat conversation between the authenticated user and an *approved* character.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Request Body:** `application/json` (`ConversationCreate` schema)
    ```json
    {
      "character_id": "string" // UUID of the approved character to chat with
    }
    ```
*   **Responses:**
    *   `201 Created`: Conversation started successfully. Returns details of the new conversation (`ConversationPublic` schema).
        ```json
        {
          "id": "...", // UUID of the new conversation
          "user_id": "...", // Current user's ID
          "character_id": "...", // Character's ID
          "created_at": "..." // ISO timestamp
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `404 Not Found`: Character with the given ID not found or is not approved.
    *   `422 Unprocessable Entity`: Validation error.

### List My Conversations

*   **Endpoint:** `GET /conversations/`
*   **Description:** Retrieve a list of conversations the currently authenticated user has participated in.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0)
    *   `limit`: `integer` (Query, Default: 100)
    *   *(Note: API spec doesn't explicitly show sorting - might default to creation/last message time)*
*   **Responses:**
    *   `200 OK`: List of conversations (`ConversationsPublic` schema).
        ```json
        {
          "data": [
            {
              "id": "...",
              "user_id": "...",
              "character_id": "...",
              "created_at": "...",
              // Potentially includes last_interaction_at, character_name, character_image_url
            }
          ],
          "count": 0 // Total count of user's conversations
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `422 Unprocessable Entity`: Invalid query parameters.

### Get Conversation Messages

*   **Endpoint:** `GET /conversations/{conversation_id}/messages`
*   **Description:** Retrieve the messages within a specific conversation belonging to the current user.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Parameters:**
    *   `conversation_id`: `string` (Path parameter, UUID format) *Required*
    *   `skip`: `integer` (Query, Default: 0) - For pagination (usually skip older messages).
    *   `limit`: `integer` (Query, Default: 100) - Max messages per request.
    *   *(Note: API spec doesn't show sorting - usually returns oldest first or newest first based on implementation)*
*   **Responses:**
    *   `200 OK`: List of messages (`MessagesPublic` schema).
        ```json
        {
          "data": [
            {
              "content": "string",
              "id": "...",
              "conversation_id": "...", // Matches path parameter
              "sender": "user", // or "character", "system"
              "timestamp": "..." // ISO timestamp
            }
          ],
          "count": 0 // Total messages in the conversation
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `403 Forbidden`: Conversation does not belong to the user.
    *   `404 Not Found`: Conversation not found.
    *   `422 Unprocessable Entity`: Invalid query parameters or UUID format.

### Send Message

*   **Endpoint:** `POST /conversations/{conversation_id}/messages`
*   **Description:** Send a message from the user to the specified conversation. The backend will automatically generate and return the character's AI response using the active AI provider. If the AI provider fails, the character's fallback response will be used.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Parameters:**
    *   `conversation_id`: `string` (Path parameter, UUID format) *Required*
*   **Request Body:** `application/json` (`MessageCreate` schema)
    ```json
    {
      "content": "string" // The user's message text (max 5000 chars)
    }
    ```
*   **Responses:**
    *   `200 OK`: Message sent and AI response generated. Returns the AI's response message (`MessagePublic` schema).
        ```json
        {
          "content": "AI response text...",
          "id": "...", // ID of the AI's message
          "conversation_id": "...",
          "sender": "ai",
          "timestamp": "..."
        }
        ```
        
        **AI Response Details:**
        - Uses the currently active AI provider (default: `gemini`)
        - Response incorporates character's personality traits, writing style, and background
        - If AI provider fails, uses character's `fallback_response` field
        - Responses are generated in real-time (typically 2-5 seconds)
        
    *   `401 Unauthorized`: Not authenticated.
    *   `403 Forbidden`: Conversation does not belong to the user.
    *   `404 Not Found`: Conversation or associated character not found.
    *   `422 Unprocessable Entity`: Validation error (e.g., message content too long or empty).
    *   `500 Internal Server Error`: AI provider error (fallback response will be used if available).

**AI Integration Notes:**
- The system automatically stores both the user message and AI response
- AI responses use the character's complete personality profile (V3 system)
- Multiple AI providers ensure high availability
- Character-specific fallback responses prevent service interruption
- Response quality varies by provider (DeepSeek Chat V3 recommended for consistency)

### Delete Conversation

*   **Endpoint:** `DELETE /conversations/{conversation_id}`
*   **Description:** Delete a conversation (and potentially its messages) belonging to the current user.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Parameters:**
    *   `conversation_id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `204 No Content`: Conversation deleted successfully.
    *   `401 Unauthorized`: Not authenticated.
    *   `403 Forbidden`: Conversation does not belong to the user.
    *   `404 Not Found`: Conversation not found.
    *   `422 Unprocessable Entity`: Invalid UUID format.

---

## Utilities (`/utils`)

### Test Email Sending

*   **Endpoint:** `POST /api/v1/utils/test-email/`
*   **Description:** Send a test email to the specified address. Requires superuser privileges.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `email_to`: `string` (Query parameter, email format) *Required*
*   **Responses:**
    *   `201 Created`: Test email sent successfully. Response body seems generic.
    *   `401 Unauthorized`/`403 Forbidden`.
    *   `422 Unprocessable Entity`: Invalid query parameter.

### Health Check

*   **Endpoint:** `GET /api/v1/utils/health-check/`
*   **Description:** Simple endpoint to check if the API is running.
*   **Responses:**
    *   `200 OK`: API is healthy.
        ```json
        true
        ```

---

## Configuration (`/config`)

*Requires superuser privileges for all endpoints.*

### AI Providers Overview

The system supports multiple AI providers for character responses:

**Core Providers:**
- **`gemini`** - Google Gemini 2.0 Flash (New API format with `google-genai` package)
- **`openai`** - Direct OpenAI GPT-4o access  
- **`claude`** - Anthropic Claude 3 Haiku (Placeholder - not fully implemented)
- **`fptai`** - FPT AI Llama 3.3 70B Instruct

**OpenRouter Model Providers** (via OpenRouter API):
- **`deepseek-r1`** - DeepSeek R1 0528 Qwen3 8B (Free)
- **`sarvam`** - Sarvam M (Free) 
- **`deepseek-chat`** - DeepSeek Chat V3 0324 (Free) ✅ **Reliable & Working**
- **`qwen3`** - Qwen 3 235B A22B (Free) ✅ **Working**
- **`gemma3`** - Google Gemma 3 27B IT (Free) ✅ **Working**

**Provider Status:**
- ✅ **Working Perfectly**: `gemini`, `deepseek-chat`, `qwen3`, `gemma3`
- ⚠️ **Available but Issues**: `sarvam` (may have model-specific quirks), `deepseek-r1`
- 🚧 **Not Implemented**: `claude`, `fptai`
- 🔧 **Direct APIs**: `openai` (requires OpenAI API key)

**Default Provider**: `gemini` (Gemini 2.0 Flash)

### Get Available AI Providers

*   **Endpoint:** `GET /config/ai/providers/available`
*   **Description:** Get a list of available (configured with API keys) AI provider names.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Responses:**
    *   `200 OK`: List of available provider names.
        ```json
        [
          "gemini",
          "deepseek-r1",
          "sarvam", 
          "deepseek-chat",
          "qwen3",
          "gemma3"
        ]
        ```
        *Note: The actual list depends on which API keys are configured in the environment.*
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.

### Get Active AI Provider

*   **Endpoint:** `GET /config/ai/providers/active`
*   **Description:** Get the name of the currently active AI provider used for generating responses.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Responses:**
    *   `200 OK`: Name of the active provider.
        ```json
        "gemini"
        ```
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.

### Set Active AI Provider

*   **Endpoint:** `PUT /config/ai/providers/active`
*   **Description:** Set the active AI provider. The provider name must be one of the available providers.
*   **Authentication:** Requires `Authorization: Bearer <token>` (Superuser).
*   **Parameters:**
    *   `provider_name`: `string` (Query parameter) *Required* - The name of the provider to activate.
        
        **Valid Values:**
        - `"gemini"` - Google Gemini 2.0 Flash
        - `"openai"` - OpenAI GPT-4o (if API key configured)
        - `"deepseek-r1"` - DeepSeek R1 via OpenRouter
        - `"sarvam"` - Sarvam M via OpenRouter  
        - `"deepseek-chat"` - DeepSeek Chat V3 via OpenRouter (Recommended)
        - `"qwen3"` - Qwen 3 235B via OpenRouter
        - `"gemma3"` - Gemma 3 27B via OpenRouter
        - `"claude"` - Claude 3 Haiku (if implemented)
        - `"fptai"` - FPT AI (if implemented)
        
*   **Responses:**
    *   `200 OK`: Provider activated successfully.
        ```json
        {
          "message": "Active AI provider set to 'gemini'"
        }
        ```
    *   `400 Bad Request`: The specified provider name is not available or not configured with API keys.
    *   `401 Unauthorized`/`403 Forbidden`: Not authenticated or insufficient permissions.
    *   `422 Unprocessable Entity`: Invalid query parameter.

**Required Environment Variables:**
- `GEMINI_API_KEY` - For Gemini provider
- `OPENAI_API_KEY` - For OpenAI provider  
- `OPENROUTER_API_KEY` - For all OpenRouter model providers (deepseek-r1, sarvam, deepseek-chat, qwen3, gemma3)
- `ANTHROPIC_API_KEY` - For Claude provider
- `FPT_AI_API_KEY` - For FPT AI provider

---

## Schemas (Complete Overview)

**Authentication & Users:**
*   **Token:** `{ access_token: string, token_type: 'bearer' }`
*   **UserPublic:** `{ email, is_active, is_superuser, full_name, id }`
*   **UserCreate (Admin):** `{ email, password, is_active?, is_superuser?, full_name? }`
*   **UserRegister (Public):** `{ email, password, full_name? }`
*   **UserUpdateMe:** `{ full_name?, email? }`
*   **UpdatePassword:** `{ current_password, new_password }`

**Characters:**
*   **CharacterPublic:** 
    ```json
    { 
      "id": "uuid", 
      "name": "string (max 100)",
      "description": "string?", 
      "image_url": "string?", 
      "greeting_message": "string?",
      "scenario": "string?",
      "category": "string?", 
      "language": "string?",
      "tags": ["string"] | "string"?,
      "voice_id": "string?",
      "personality_traits": "string?",
      "writing_style": "string?", 
      "background": "string?",
      "knowledge_scope": "string?",
      "quirks": "string?",
      "emotional_range": "string?",
      "popularity_score": "integer",
      "status": "pending|approved|rejected",
      "is_public": "boolean",
      "is_featured": "boolean", 
      "creator_id": "uuid",
      "created_at": "datetime",
      "updated_at": "datetime"
      // admin_feedback & fallback_response excluded from public view
    }
    ```
*   **CharacterAdmin:** 
    ```json
    { 
      "id": "uuid", 
      "name": "string (max 100)",
      "description": "string?", 
      "image_url": "string?", 
      "greeting_message": "string?",
      "scenario": "string?",
      "category": "string?", 
      "language": "string?",
      "tags": ["string"] | "string"?,
      "voice_id": "string?",
      "personality_traits": "string?",
      "writing_style": "string?", 
      "background": "string?",
      "knowledge_scope": "string?",
      "quirks": "string?",
      "emotional_range": "string?",
      "popularity_score": "integer",
      "status": "pending|approved|rejected",
      "is_public": "boolean",
      "is_featured": "boolean", 
      "creator_id": "uuid",
      "created_at": "datetime",
      "updated_at": "datetime",
      "admin_feedback": "string?",     // Admin-only field
      "fallback_response": "string?"   // Admin-only field
    }
    ```
*   **CharacterCreate:** 
    ```json
    { 
      "name": "string (required)",
      "description": "string?", 
      "image_url": "string?",
      "greeting_message": "string?", 
      "scenario": "string?",
      "category": "string?",
      "language": "string?",
      "tags": ["string"] | "string"?,
      "voice_id": "string?",
      "personality_traits": "string?",
      "writing_style": "string?",
      "background": "string?",
      "knowledge_scope": "string?", 
      "quirks": "string?",
      "emotional_range": "string?"
    }
    ```
*   **CharacterUpdateAdmin:** `{ name?, description?, image_url?, greeting_message?, status?, category?, tags?, scenario?, language?, personality_traits?, writing_style?, background?, knowledge_scope?, quirks?, emotional_range?, is_public?, is_featured?, admin_feedback?, fallback_response? }`
*   **CharactersPublic:** `{ data: CharacterPublic[], count: integer }`

**Conversations:**
*   **ConversationPublic:** `{ id, user_id, character_id, created_at, last_interaction_at?, character_name?, character_image_url? }`
*   **ConversationCreate:** `{ character_id }`
*   **ConversationsPublic:** `{ data: ConversationPublic[], count: integer }`

**Messages:**
*   **MessagePublic:** 
    ```json
    { 
      "content": "string (max 5000)", 
      "id": "uuid", 
      "conversation_id": "uuid", 
      "sender": "user|ai", 
      "timestamp": "datetime" 
    }
    ```
*   **MessageCreate:** `{ content: "string (max 5000)" }`
*   **MessagesPublic:** `{ data: MessagePublic[], count: integer }`

**AI Configuration:**
*   **AIProviderConfigPublic:** `{ active_provider_name: string }`
*   **Available Providers:** Array of strings from: `["gemini", "openai", "deepseek-r1", "sarvam", "deepseek-chat", "qwen3", "gemma3", "claude", "fptai"]`

**Enums:**
*   **CharacterStatus:** `"pending" | "approved" | "rejected"`
*   **MessageSender:** `"user" | "ai"`

**Validation & Errors:**
*   **HTTPValidationError:** Standard FastAPI validation error response with `detail` array containing location, message, and type information.

**Field Notes:**
- Optional fields indicated by `?`
- All `id` fields are UUID format
- Text fields (`description`, `greeting_message`, `scenario`, personality fields) support unlimited length
- `tags` field accepts both JSON arrays and comma-separated strings
- `timestamp` and date fields are ISO 8601 datetime strings
- `sender` field in messages uses `"ai"` (not `"character"`) for consistency
