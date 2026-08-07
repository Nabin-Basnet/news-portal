# News Portal API Documentation

This project exposes a Django REST Framework API for:
- user authentication and profile management
- article creation, review, publishing, comments, reactions, and bookmarks
- category/tag management
- advertisement delivery and interaction tracking

## 1. Quick start

- Base URL for local development: http://localhost:8000
- Live hosted backend base URL: https://news-portal-hvgs.onrender.com
- Live hosted Swagger UI: https://news-portal-hvgs.onrender.com/api/docs/
- Live hosted OpenAPI schema: https://news-portal-hvgs.onrender.com/api/schema/
- Live hosted ReDoc: https://news-portal-hvgs.onrender.com/api/redoc/

### Authentication
The API uses JWT authentication.

1. Login with:
   - POST /api/token/
   - body: {"email": "user@example.com", "password": "secret"}
2. Copy the access token from the response.
3. Send it in the Authorization header:
   - Authorization: Bearer <access_token>
4. Refresh when the token expires:
   - POST /api/token/refresh/

### Common response patterns
- 200 OK: successful read/update
- 201 Created: successful create
- 204 No Content: successful delete
- 400 Bad Request: validation error
- 401 Unauthorized: missing/invalid token
- 403 Forbidden: authenticated but not allowed
- 404 Not Found: resource missing
- 405 Method Not Allowed: wrong method

### Pagination
List endpoints return paginated results with fields like:
- count
- next
- previous
- results

### Media uploads
Article images and profile pictures use multipart/form-data. For those requests, use a form-data body instead of JSON.

---

## 2. Roles and permissions

The app recognizes these role names:
- admin
- editor
- staff
- reporter
- user

The role is stored on the user model as a foreign key to the Role table. Public registration always creates a user with the default User role.

### Role matrix

| Area | Anonymous | User | Reporter | Staff | Editor | Admin |
|---|---|---|---|---|---|---|
| Register account | Yes | - | - | - | - | - |
| Login / refresh token | Yes | Yes | Yes | Yes | Yes | Yes |
| View published articles | Yes | Yes | Yes | Yes | Yes | Yes |
| Create article | No | No | Yes | Yes | Yes | Yes |
| Edit own draft article | No | No | Yes | Yes | Yes | Yes |
| Edit any article | No | No | No | Yes (non-published) | Yes | Yes |
| Submit article for review | No | No | Yes (own article) | Yes (own/reporter article) | Yes | Yes |
| Review / approve / reject | No | No | No | Yes (via workflow) | Yes | Yes |
| Publish article | No | No | No | No | Yes | Yes |
| Manage categories/tags | No | No | No | No | Yes | Yes |
| Manage users/roles | No | No | No | No | No | Yes |
| Create/update/delete ads | No | No | No | No | No | Yes |

### Permission notes
- For articles, the workflow is controlled by the article status.
- Users can comment, react, and bookmark only on published articles.
- Admins can assign roles through the role endpoint.

---

## 3. Authentication and user APIs

### 3.1 Login
- Method: POST
- URL: /api/token/
- Access: public
- Body:
  ```json
  {
    "email": "frontend@example.com",
    "password": "secret123"
  }
  ```
- Response:
  ```json
  {
    "refresh": "...",
    "access": "..."
  }
  ```

### 3.2 Refresh token
- Method: POST
- URL: /api/token/refresh/
- Access: public
- Body:
  ```json
  {
    "refresh": "..."
  }
  ```

### 3.3 Register user
- Method: POST
- URL: /api/users/
- Access: public
- Body:
  ```json
  {
    "email": "frontend@example.com",
    "first_name": "Frontend",
    "last_name": "Dev",
    "password": "secret123",
    "password2": "secret123",
    "bio": "Frontend developer"
  }
  ```
- Notes:
  - The new account receives the default User role.
  - Admin-only role changes are done through the set-role endpoint.

### 3.4 Get current user profile
- Method: GET
- URL: /api/users/me/
- Access: authenticated user
- Response includes id, email, first_name, last_name, bio, profile_pic, role, is_verified, is_active, created_at, updated_at.

### 3.5 Change password
- Method: POST
- URL: /api/users/change-password/
- Access: authenticated user
- Body:
  ```json
  {
    "old_password": "secret123",
    "new_password": "newSecret123",
    "new_password2": "newSecret123"
  }
  ```

### 3.6 Logout
- Method: POST
- URL: /api/users/logout/
- Access: authenticated user
- Body options:
  ```json
  {
    "all": true
  }
  ```
  or
  ```json
  {
    "token_id": 12
  }
  ```

### 3.7 List users
- Method: GET
- URL: /api/users/
- Access: admin only

### 3.8 Get one user
- Method: GET
- URL: /api/users/{id}/
- Access: self or admin

### 3.9 Update user
- Method: PUT / PATCH
- URL: /api/users/{id}/
- Access: self or admin
- Notes:
  - Regular users can update their own profile only.
  - Admins can update any user.

### 3.10 Delete user
- Method: DELETE
- URL: /api/users/{id}/
- Access: self or admin

### 3.11 Assign role to user
- Method: POST
- URL: /api/users/{id}/set-role/
- Access: admin only
- Body:
  ```json
  {
    "role_id": 2
  }
  ```

### 3.12 Roles APIs
- List: GET /api/roles/
- Create: POST /api/roles/
- Retrieve: GET /api/roles/{id}/
- Update: PUT/PATCH /api/roles/{id}/
- Delete: DELETE /api/roles/{id}/
- Access: admin only

---

## 4. Article APIs

### 4.1 List articles (public feed)
- Method: GET
- URL: /articles/
- Access: public
- Notes:
  - Returns only published articles.
  - Supports pagination.

### 4.2 Create article
- Method: POST
- URL: /articles/ or /articles/create/
- Access: reporter/staff/editor/admin
- Body (form-data or JSON):
  ```json
  {
    "title": "New article",
    "summary": "Short summary",
    "body": "Main article body",
    "category_id": 1,
    "category_name": "Sports",
    "author_name": "Optional display name"
  }
  ```
- For image upload, include a field named image.
- Notes:
  - New articles are created as draft by default.
  - The author is automatically assigned from the authenticated user.

### 4.3 Get one article
- Method: GET
- URL: /articles/{id}/
- Access:
  - public for published articles
  - authenticated author/editor/staff/admin can also view non-published articles
- Response includes article details, comments, reactions, and counts.

### 4.4 Update article
- Method: PUT / PATCH
- URL: /articles/{id}/update/
- Access:
  - Admin/editor can edit any article
  - Reporter can edit own draft article
  - Staff can edit own article or reporter article when status is not published
- Body example:
  ```json
  {
    "title": "Updated title",
    "summary": "Updated summary",
    "body": "Updated body"
  }
  ```

### 4.5 Delete article
- Method: DELETE
- URL: /articles/{id}/delete/
- Access:
  - Admin can delete any article
  - Editor can delete non-published articles
  - Reporter/staff can delete own draft articles

### 4.6 Submit article for review
- Method: POST
- URL: /articles/{id}/submit/
- Access: reporter/staff/editor/admin
- Notes:
  - Draft or rejected articles can be submitted.
  - The article moves to the submitted state.

### 4.7 Start review
- Method: POST
- URL: /articles/{id}/start-review/
- Access: editor/admin or staff with review rights
- Notes:
  - Moves a submitted article to under_review.

### 4.8 Approve article
- Method: POST
- URL: /articles/{id}/approve/
- Access: editor/admin
- Notes:
  - Only articles in under_review may be approved.

### 4.9 Reject article
- Method: POST
- URL: /articles/{id}/reject/
- Access: editor/admin
- Body:
  ```json
  {
    "note": "Content needs revision"
  }
  ```

### 4.10 Request revision
- Method: POST
- URL: /articles/{id}/request-revision/
- Access: staff/editor/admin
- Body:
  ```json
  {
    "note": "Please improve the headline"
  }
  ```
- Notes:
  - Staff can return reporter articles only.

### 4.11 Publish article
- Method: POST
- URL: /articles/{id}/publish/
- Access: editor/admin
- Notes:
  - Only approved articles can be published.

### 4.12 Archive article
- Method: POST
- URL: /articles/{id}/archive/
- Access: editor/admin

### 4.13 Pending articles queue
- Method: GET
- URL: /articles/pending/
- Access: editor/admin
- Notes:
  - Returns submitted and under_review articles.

### 4.14 Draft articles queue
- Method: GET
- URL: /articles/drafts/
- Access: staff/editor/admin
- Notes:
  - Returns draft articles.

### 4.15 Reporter article list
- Method: GET
- URL: /articles/reporter/articles/
- Access: authenticated editorial user
- Notes:
  - Returns the authenticated reporter’s articles.

### 4.16 Admin article list

- Method: `GET`
- URL: `/api/articles/admin/articles/`
- Access: admin only
- Returns: every article status, paginated using the standard `count`, `next`, `previous`, and `results` response shape.
- Optional query parameters:
  - `status`: one of `draft`, `submitted`, `under_review`, `approved`, `published`, `rejected`, or `archived`.
  - `search`: title, summary, body, author, or category search.
  - `ordering`: `title`, `status`, `created_at`, `updated_at`, `published_at`, `view_count`, `comment_count`, `reaction_count`, or `bookmark_count`; prefix with `-` for descending order.
- Each result includes status, author, category, workflow timestamps, and engagement counts.
- `featured` is currently always `false`, because the Article model has no persisted featured field.

### 4.17 Admin activity dashboard
- Method: GET
- URL: /articles/admin/activity/
- Access: admin only
- Response includes article counts, engagement counts, and categories.

### 4.18 Public feeds and discovery
- GET /articles/feed/
  - Alias for the main published article list.
- GET /articles/trending/
  - Returns the most-viewed published articles.
- GET /articles/news-of-the-day/
  - Returns the most-viewed article from the last 24 hours, or fallback newest published article.
- GET /articles/search/?q=keyword&category=sports
  - Search by title/body and filter by category slug.
- GET /articles/tag/{slug}/
  - Returns published articles linked to a tag.

### 4.19 Categories and tags
- List categories: GET /articles/categories/
- Create category: POST /articles/categories/
- Retrieve/update/delete category: GET/PUT/PATCH/DELETE /articles/categories/{id}/
- Access for create/update/delete: editor/admin
- List tags: GET /articles/tags/
- Create/update/delete tags: POST/PUT/PATCH/DELETE /articles/tags/
- Access for create/update/delete: staff/editor/admin

### 4.20 Comments
- GET /articles/{id}/comments/
  - Get comments for an article.
- POST /articles/{id}/comments/
  - Create a comment on a published article.
- Body:
  ```json
  {
    "content": "Great article"
  }
  ```
- Optional reply:
  ```json
  {
    "content": "Reply to this comment",
    "parent_id": 12
  }
  ```
- Notes:
  - Comments are only allowed on published articles.

### 4.21 Reactions
- POST /articles/{id}/react/
- Body:
  ```json
  {
    "reaction_type": "like"
  }
  ```
- Allowed values: like, love, wow, sad.
- Notes:
  - Reactions are only available on published articles.
  - Sending the same reaction again removes it.

### 4.22 Bookmarks
- GET /articles/{id}/bookmarks/
  - Returns whether the current user has bookmarked the article.
- POST /articles/{id}/bookmark/
  - Toggles the bookmark state.
- GET /articles/my-bookmarks/
  - Returns all bookmarks for the authenticated user.

---

## 5. Advertisement APIs

### 5.1 List ads for frontend rendering
- Method: GET
- URL: /api/ads/
- Access: public
- Notes:
  - Returns active ads grouped by position.
  - Supports category targeting: /api/ads/?category=sports
  - The response shape is a map such as top_banner, sidebar, in_article, footer, popup.

### 5.2 Create and edit advertisements

- Create: `POST /api/ads/`
- Update/delete: `PUT`, `PATCH`, or `DELETE /api/ads/{id}/`
- Access: staff and admins may create; staff may edit or delete only their own draft advertisements; admins may manage any advertisement.
- New advertisements are always created with `draft` status, regardless of client input.
- For image upload, send multipart form-data.

### 5.3 Advertisement workflow

- `POST /api/ads/{id}/submit/`: staff owner or admin; draft/rejected ? submitted.
- `POST /api/ads/{id}/start-review/`: editor/admin; submitted ? under_review.
- `POST /api/ads/{id}/approve/`: editor/admin; under_review ? approved.
- `POST /api/ads/{id}/reject/`: editor/admin; submitted/under_review/approved ? rejected. Accepts optional `note`.
- `POST /api/ads/{id}/publish/`: editor/admin; approved ? published.
- `POST /api/ads/{id}/archive/`: editor/admin; moves an advertisement to archived.

Only `published`, active, in-schedule advertisements appear in public delivery, trending, click, and impression endpoints.

### 5.4 Admin advertisement list

- Method: `GET`
- URL: `/api/ads/admin/ads/`
- Access: admin only
- Returns all advertisement statuses with creator, reviewer, dates, active state, click count, and impression count.
- Optional query parameters: `status`, `search`, `ordering`, and `page`.
- Valid status values: `draft`, `submitted`, `under_review`, `approved`, `published`, `rejected`, `archived`.

### 5.5 Track ad impression
- Method: POST
- URL: /api/ads/impressions/
- Access: public
- Body:
  ```json
  {
    "ad_id": 4
  }
  ```

### 5.6 Track ad click
- Method: POST
- URL: /api/ads/click/
- Access: public
- Body:
  ```json
  {
    "ad_id": 4
  }
  ```

### 5.7 Trending ads
- Method: GET
- URL: /api/ads/trending/
- Access: public

---

## 6. Suggested frontend integration flow

1. Call POST /api/token/ to get a JWT.
2. Save the access token in memory or local storage.
3. Add the token to each authenticated request as Authorization: Bearer <token>.
4. For public pages, call the article and ad endpoints without authentication.
5. For article creation/editing, use form-data and include the image if relevant.
6. Use the article workflow endpoints in order:
   - create draft
   - submit
   - start review
   - approve/reject
   - publish

---

## 7. Important implementation details for frontend developers

- The user model uses email as the login identifier, not username.
- The API uses JSON for most endpoints, but file uploads must use multipart/form-data.
- Article create/update endpoints accept category_id or category_name; category_name is validated against existing categories.
- Public article routes only return published articles.
- Comments, reactions, and bookmarks are available on published articles only.
- The API is already documented through the Swagger UI at /api/docs/.

If you want, the next step can be to generate a frontend-ready Postman collection or a dedicated OpenAPI export for this project.
