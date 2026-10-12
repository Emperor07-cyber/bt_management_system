# BT Management System

Asset, inventory, fleet, procurement, finance, approvals, audit, reporting, and company-management system.

The project has two parts:

- backend/: Django REST API backed by PostgreSQL.
- frontend/: React/Vite web application.

## Requirements

Install these on the computer that will run the application:

- Windows 10 or newer
- Python 3.14 or a compatible supported Python version
- Node.js and npm
- PostgreSQL

PostgreSQL is the database server. Django is the application framework; Django does not replace the database.

## Project layout

- backend/ — Django project and API applications
- frontend/ — React/Vite application
- deployment/ — Windows setup and start/stop scripts
- .env.example — development environment template

## First-time local setup

Open PowerShell in the project root.

### 1. Create the backend environment

    cd backend
    py -m venv venv
    .\venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    cd ..

Do not copy backend/venv between computers. Virtual environments contain computer-specific paths and must be recreated on each computer.

### 2. Configure PostgreSQL

Create a PostgreSQL database and user, then copy .env.example to .env and update the values:

    Copy-Item .env.example .env

The important database settings are:

    DB_NAME=bt_management
    DB_USER=postgres
    DB_PASSWORD=your-postgres-password
    DB_HOST=localhost
    DB_PORT=5432

Never commit or distribute .env. It contains passwords and the Django secret key.

### 3. Run migrations

    cd backend
    .\venv\Scripts\python.exe manage.py migrate
    .\venv\Scripts\python.exe manage.py createsuperuser
    cd ..

### 4. Start the development servers

In one PowerShell window:

    cd backend
    .\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

In another PowerShell window:

    cd frontend
    npm install
    npm run dev

The development frontend normally runs at http://localhost:5173 and the API at http://127.0.0.1:8000.

## Windows deployment setup

The deployment scripts run the production-style local installation with Waitress. The frontend is built and served locally on port 8080; the API runs on port 8000.

1. Install Python, Node.js, npm, and PostgreSQL.
2. Ensure PostgreSQL is running.
3. Open Command Prompt as Administrator in the project root.
4. Run:

    deployment\setup_windows.bat

The setup script will:

- recreate the backend virtual environment for the current computer;
- install Python dependencies;
- create/configure the PostgreSQL database and application user;
- run Django migrations;
- collect static files;
- install and build the frontend;
- create deployment settings.

After setup completes, start the application with:

    deployment\start_system.bat

Open http://127.0.0.1:8080 in a browser. Stop the services with:

    deployment\stop_system.bat

Logs are written to deployment\logs.

The setup script can install from local package caches when they are supplied under deployment\packages. Otherwise, it downloads dependencies from PyPI and npm, so internet access is required during setup.

## Frontend API configuration

The frontend reads the API URL from VITE_API_BASE_URL during the Vite build. If it is not supplied, it defaults to:

    http://127.0.0.1:8000/api/v1

For a different backend host, create frontend/.env.production before building:

    VITE_API_BASE_URL=http://your-server:8000/api/v1

The Windows deployment script generates the local value automatically.

## Useful management commands

Run these from backend/ with the virtual environment active:

    python manage.py check
    python manage.py check --deploy
    python manage.py showmigrations
    python manage.py makemigrations
    python manage.py migrate
    python manage.py collectstatic --noinput
    python manage.py createsuperuser

Run backend tests with:

    python manage.py test

## Database backup and restore

Back up the PostgreSQL database before moving or reinstalling the application:

    pg_dump -h localhost -p 5432 -U postgres -Fc bt_management > bt_management.backup

Restore it into an existing database with:

    pg_restore -h localhost -p 5432 -U postgres -d bt_management --clean --if-exists bt_management.backup

Keep database backups separate from the source-code folder.

## Troubleshooting

### Could not connect to server

PostgreSQL is not running, the port is wrong, or the database credentials in .env are incorrect. Confirm that PostgreSQL is listening on the configured DB_PORT.

### Frontend build was not found

Run npm install and npm run build inside frontend/, or run the complete deployment setup script.

### Waitress was not found

The backend production dependencies were not installed. Run deployment\setup_windows.bat or install the production requirements into the backend virtual environment.

### Port already in use

The default ports are 8000 for the API and 8080 for the frontend. Stop the process using the port or change the deployment scripts and frontend API configuration consistently.

## Security notes

- Use DEBUG=False for deployment.
- Generate a new strong SECRET_KEY for every installation.
- Use a strong PostgreSQL password.
- Do not commit .env, database backups, virtual environments, node_modules, or generated frontend files.
- For access from other computers, configure allowed hosts, CORS, firewall rules, and HTTPS before exposing the application beyond the local machine.
