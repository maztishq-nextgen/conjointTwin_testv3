JWT-based authentication with bcrypt password hashing, FastAPI HTTPBearer middleware, and JSON file-based user storage. Key flows include user registration [1c], login with token generation [2d], protected endpoint access via dependency injection [3b], and token refresh [4c]. API usage is tracked per user [5e].

1
User Registration Flow
Handles new user signup from API endpoint through password hashing to database persistence. See more
User Registration Flow
FastAPI Application
1a
Signup Endpoint
Validate request body (UserCreate)
1b
Check Existing User
user_db.get_user_by_email()
1c
Create User
UserDatabase.create_user()
Generate UUID for user
1d
Hash Password
1e
Bcrypt Hashing
pwd_context.hash()
Build user_data dict
1f
Persist to Database
_save_db()
Return UserResponse (without password)
2
Login & JWT Token Generation
Authenticates user credentials and generates access/refresh JWT tokens. See more
Login & JWT Token Generation Flow
FastAPI Application
2a
Login Endpoint
2b
Retrieve User
user_db.get_user_by_email()
2c
Verify Password
verify_password() in core/auth.py
pwd_context.verify()
2d
Generate Tokens
create_tokens() in core/auth.py
2e
Create Access Token
create_access_token()
2f
JWT Encoding
Create refresh token
create_refresh_token()
JWT encode (7-day expiry)
Return Token response
{access_token, refresh_token, type}
3
Protected Endpoint Authentication
Validates JWT tokens via dependency injection for protected API endpoints. See more
Protected Endpoint Authentication Flow
FastAPI Request Handler
3a
Protected Endpoint
Depends(get_current_user)
3b
Auth Dependency
Depends(security: HTTPBearer)
3c
Extract Token
3d
Decode JWT
3e
JWT Verification
3f
Fetch User
Validate user is_active
Authenticated Endpoint Execution
3g
User Context Usage
Uses current_user.id for authz
4
Token Refresh Flow
Exchanges refresh token for new access and refresh tokens without re-authentication. See more
Token Refresh Flow
4a
Refresh Endpoint
4b
Validate Refresh Token
jwt.decode() validates signature
extracts user_id from payload
4c
Verify User Active
loads users.json
validates user.is_active
4d
Issue New Tokens
create_access_token()
jwt.encode() with 6hr expiry
create_refresh_token()
4e
Refresh Token Expiry
return Token(access, refresh)
5
API Usage Tracking
Tracks token consumption and costs per authenticated user after API calls. See more
API Usage Tracking Flow
expand_topic() endpoint
5a
Capture Start Cost
captures initial cost state
[process knowledge graph request]
OpenAI API calls accumulate costs
5b
Capture End Cost
captures final cost state
calculate delta
5c
Calculate Request Cost
5d
Calculate Token Usage
5e
Update User Usage
load user record from JSON
5f
Increment Request Count
usage["total_tokens"] += tokens
usage["total_cost"] += cost
5g
Persist Usage Data
persist to users.json
6
User Data Persistence Layer
Thread-safe JSON file-based storage for user accounts and authentication data. See more
UserDatabase Class (user_db.py)
6a
Database Initialization
Initialize db_path & thread lock
Create empty JSON if not exists
6b
Load Database
6d
Thread Safety
6c
Read JSON File
Convert ISO datetime strings
_save_db() writes to disk
6d
Thread Safety
Serialize user data to JSON
6e
Write JSON File
6f
Email Lookup
Call _load_db()
Iterate users to find email match
get_user_by_id() lookup
Call _load_db()
Direct dictionary key lookup
create_user() / update_user_api_usage()
Call _load_db()
Modify user data in memory
Call _save_db() to persist