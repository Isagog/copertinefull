# Local Development Setup

## Initial Setup

```bash
# Install backend dependencies and set up database
cd backend
poetry install
poetry install --no-root  # Install the package in development mode

# Generate a secret key and add it to .env
poetry run copertine-cli generate-secret  # Copy the output to .env

# Initialize or reset the database
poetry run copertine-cli init-db     # First-time initialization
# OR if tables already exist:
poetry run copertine-cli reset-db    # Reset existing database (⚠️ Deletes all data)
```

Create or update your `.env` file in the backend directory with:
```
# Database
DATABASE_URL=sqlite:///./sql_app.db

# Security
SECRET_KEY=<paste-generated-secret-here>

# Email Configuration (for development)
MAIL_USERNAME=any
MAIL_PASSWORD=any
MAIL_FROM=test@example.com
MAIL_PORT=1025
MAIL_SERVER=localhost
MAIL_STARTTLS=False
MAIL_SSL_TLS=False

# Frontend URL
FRONTEND_URL=http://localhost:3000
```

## Running the Application

1. Start the email testing server (choose one option):

   Option A - Using Mailpit (recommended):
   ```bash
   docker-compose up mailpit -d
   ```
   Access Mailpit web interface at http://localhost:8025 to view sent emails
   
   Features:
   - Modern, actively maintained SMTP testing server
   - Real-time email testing
   - Clean web interface
   - No storage limitations

   Option B - Using Python's built-in SMTP server:
   ```bash
   python -m smtpd -c DebuggingServer -n localhost:1025
   ```

2. Start the backend:
   ```bash
   cd backend
   poetry run uvicorn src.main:app --reload
   ```

3. Start the frontend:
   ```bash
   cd frontend
   pnpm dev
   ```

4. Access the application at http://localhost:3000

## Authentication Features

- User registration with domain restriction (manifesto.it and isagog.com)
- Email verification required before login
- Password requirements:
  - Minimum 8 characters
  - Additional requirements can be configured in `frontend/app/lib/config/auth.ts`
- Password reset functionality
- Protected routes

## Development Notes

- All authentication-related frontend components are in `frontend/app/components/auth/`
- Backend authentication logic is in `backend/src/includes/auth.py` and `backend/src/routes/auth.py`
- Database migrations are managed with Alembic
- Email templates are in `backend/src/includes/email_templates/`
