# Imacall API Documentation (Version 0.1.0)

This document describes the API endpoints for the Imacall application, based on the OpenAPI 3.1 specification available at `/api/v1/openapi.json`.

**Base URL:** `https://imacall-backend.onrender.com/api/v1`

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

## Characters (`/characters`)

### List Approved Characters (Public)

*   **Endpoint:** `GET /characters/`
*   **Description:** Retrieve a list of publicly available, approved characters.
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0)
    *   `limit`: `integer` (Query, Default: 100)
    *   *(Note: API spec doesn't explicitly show filters like category, tags, search, sort - these might be handled client-side or undocumented)*
*   **Responses:**
    *   `200 OK`: List of approved characters (`CharactersPublic` schema).
        ```json
        {
          "data": [
            {
              "name": "string",
              "description": "string",
              "image_url": "string",
              "greeting_message": "string",
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
              "status": "approved", // Will always be 'approved' for this endpoint
              "creator_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
              // Potentially includes other fields like category, tags, averageRating, ratingCount, etc.
            }
          ],
          "count": 0 // Total number of approved characters
        }
        ```
    *   `422 Unprocessable Entity`: Invalid query parameters.

### Get Approved Character by ID (Public)

*   **Endpoint:** `GET /characters/{id}`
*   **Description:** Get details for a specific publicly available, approved character.
*   **Parameters:**
    *   `id`: `string` (Path parameter, UUID format) *Required*
*   **Responses:**
    *   `200 OK`: Character details (`CharacterPublic` schema).
        ```json
        {
          "name": "string",
          "description": "string",
          "image_url": "string",
          "greeting_message": "string",
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "status": "approved",
          "creator_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
          // Potentially includes other fields
        }
        ```
    *   `404 Not Found`: Character not found or is not approved/public.
    *   `422 Unprocessable Entity`: Invalid UUID format.

### Submit Character for Review

*   **Endpoint:** `POST /characters/submit`
*   **Description:** Submit a new character definition. It will be created with `pending` status and requires admin approval.
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Request Body:** `application/json` (`CharacterCreate` schema)
    ```json
    {
      "name": "string", // Required (max 100 chars)
      "description": "string", // Optional
      "image_url": "string", // Optional (URL)
      "greeting_message": "string", // Optional
      // Other fields like category, tags, scenario, language might be included here based on schema evolution
    }
    ```
*   **Responses:**
    *   `201 Created`: Character submitted successfully. Returns the created character details (`CharacterPublic` schema) with `pending` status.
        ```json
        {
          "name": "string",
          "description": "string",
          "image_url": "string",
          "greeting_message": "string",
          "id": "...",
          "status": "Pending", // Corrected based on frontend types
          "creator_id": "..."
          // etc.
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `422 Unprocessable Entity`: Validation error (e.g., name too long).

### List My Character Submissions

*   **Endpoint:** `GET /characters/my-submissions`
*   **Description:** Retrieve all characters submitted by the currently authenticated user, regardless of their status (Pending, Approved, Rejected).
*   **Authentication:** Requires `Authorization: Bearer <token>`.
*   **Parameters:**
    *   `skip`: `integer` (Query, Default: 0)
    *   `limit`: `integer` (Query, Default: 100)
*   **Responses:**
    *   `200 OK`: List of the user's character submissions (`CharactersPublic` schema).
        ```json
        {
          "data": [
            {
              "name": "string",
              "description": "string",
              // ... other CharacterPublic fields ...
              "id": "...",
              "status": "Pending", // or "Approved", "Rejected"
              "creator_id": "..." // Will match the authenticated user's ID
            }
          ],
          "count": 0 // Total number of submissions by the user
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `422 Unprocessable Entity`: Invalid query parameters.

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
*   **Description:** Send a message from the user to the specified conversation. The backend will typically generate and return the character's response message.
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
          "sender": "character",
          "timestamp": "..."
        }
        ```
    *   `401 Unauthorized`: Not authenticated.
    *   `403 Forbidden`: Conversation does not belong to the user.
    *   `404 Not Found`: Conversation or associated character not found.
    *   `422 Unprocessable Entity`: Validation error (e.g., message content too long).
    *   `5xx Server Error`: Potential error during AI response generation.

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

## Schemas (Simplified Overview)

*   **Token:** `{ access_token: string, token_type: 'bearer' }`
*   **UserPublic:** `{ email, is_active, is_superuser, full_name, id }`
*   **UserCreate (Admin):** `{ email, password, is_active?, is_superuser?, full_name? }`
*   **UserRegister (Public):** `{ email, password, full_name? }`
*   **UserUpdateMe:** `{ full_name?, email? }`
*   **UpdatePassword:** `{ current_password, new_password }`
*   **CharacterPublic:** `{ name, description?, image_url?, greeting_message?, id, status, creator_id, category?, tags?, averageRating?, ratingCount?, isPublic?, createdAt?, updatedAt? }`
*   **CharacterCreate:** `{ name, description?, image_url?, greeting_message?, category?, tags?, scenario?, language? }`
*   **CharacterUpdateAdmin:** `{ name?, description?, image_url?, greeting_message?, status?, category?, tags?, scenario?, language?, isPublic?, adminFeedback? }`
*   **CharactersPublic:** `{ data: CharacterPublic[], count: integer }`
*   **ConversationPublic:** `{ id, user_id, character_id, created_at, lastInteractionAt?, characterName?, characterImageUrl? }`
*   **ConversationCreate:** `{ character_id }`
*   **ConversationsPublic:** `{ data: ConversationPublic[], count: integer }`
*   **MessagePublic:** `{ content, id, conversation_id, sender: ('user'|'character'|'system'), timestamp }`
*   **MessageCreate:** `{ content }`
*   **MessagesPublic:** `{ data: MessagePublic[], count: integer }`
*   **HTTPValidationError:** Standard FastAPI validation error response.

*(Note: Optional fields indicated by `?`. Default values and constraints like string lengths are omitted for brevity but present in the full schema.)*
