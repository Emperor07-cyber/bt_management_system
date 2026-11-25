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

If the project was copied from another computer and Python reports that it cannot find an executable, the virtual environment is stale. From the project root, recreate it on the current computer:

    Remove-Item -Recurse -Force backend\venv
    cd backend
    py -m venv venv
    .\venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    cd ..

Do not copy `.venv`, `.venv-1`, or `backend\venv` between computers. Keep the source code and dependency files, but create a new environment locally.

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

## Dashboard access and module permissions

The dashboard uses two kinds of administrators:

- A Django superuser created with `createsuperuser` has full access to every API module. The account must have `status=ACTIVE`.
- A normal user receives access through application roles. A role is linked to a user through `UserRole`, and module permissions are linked to that role through `RolePermission`.

If a user can log in but every module returns `403 Forbidden`, check that the user is active and has the correct role assignments. Logging in as a Django superuser does not require adding role rows after the permission fix in `backend/authentication/permissions.py`.

### Permission codes

Permissions follow the format `MODULE_ACTION`:

| Module | Code prefix | Actions |
| --- | --- | --- |
| Inventory | `INVENTORY` | `READ`, `CREATE`, `UPDATE`, `DELETE` |
| Fleet | `FLEET` | `READ`, `CREATE`, `UPDATE`, `DELETE` |
| Assets | `ASSET` | `READ`, `CREATE`, `UPDATE`, `DELETE` |
| Finance | `FINANCE` | `READ`, `CREATE`, `UPDATE`, `DELETE` |
| Procurement | `PROCUREMENT` | `READ`, `CREATE`, `UPDATE`, `DELETE` |
| Reports | `REPORTS` | `READ` |
| Company | `COMPANY` | `READ`, `CREATE`, `UPDATE`, `DELETE` |

For example, `INVENTORY_READ` allows viewing inventory and `FINANCE_UPDATE` allows updating finance records. The HTTP method is translated automatically: `GET` is `READ`, `POST` is `CREATE`, `PUT/PATCH` is `UPDATE`, and `DELETE` is `DELETE`.

### Give the existing Admin role company access

The project includes a safe command that creates the Company permissions and assigns them to the existing `Admin` role. Run it from `backend/`:

    python manage.py setup_company_permissions

This command does not create or delete users and does not remove existing role assignments. The existing `Admin` role must also have the permissions for the other modules listed above. For a global administrator, use a Django superuser instead.

### Check or change access in Django shell

Run:

    python manage.py shell

Then inspect or assign a role:

    from authentication.models import User, Role, UserRole
    user = User.objects.get(username="admin@example.com")
    role = Role.objects.get(name="Admin")
    UserRole.objects.get_or_create(user=user, role=role)

To assign one permission to a role:

    from authentication.models import Permission, RolePermission
    permission = Permission.objects.get(permission_code="INVENTORY_READ")
    RolePermission.objects.get_or_create(role=role, permission=permission)

After changing access, log out and log in again so the frontend obtains a fresh JWT. The API remains the final authority; hiding a menu item in the frontend alone does not grant or revoke access.

### Complete Django access checklist

When moving the project to another computer, check all of the following in the Django database. These values are stored in PostgreSQL and are not recreated just because the backend starts successfully.

#### 1. Confirm which kind of admin account is being used

There are two separate concepts:

- `is_superuser=True`: global Django/API administrator. The application permission class grants this user every active module permission.
- `is_staff=True`: allows access to Django Admin at `/admin/`. It does not by itself grant access to the dashboard API modules.
- Application role `Admin`: a normal application role. It only grants the individual `RolePermission` records assigned to it.

An account can be allowed into `/admin/` but still receive `403 Forbidden` from dashboard modules if it is only `is_staff=True` or has an empty application role.

Inspect the account:

    python manage.py shell

    from authentication.models import User
    user = User.objects.get(username="admin@example.com")
    print(user.is_active, user.is_staff, user.is_superuser, user.status)
    print(list(user.user_roles.values_list("role__name", flat=True)))

The application status must be `ACTIVE`. An inactive or locked account is denied even when it has roles or is a superuser.

#### 2. Make an account a full administrator

For a new account:

    python manage.py createsuperuser

For an existing account, change it deliberately in the Django shell:

    from authentication.models import User
    user = User.objects.get(username="admin@example.com")
    user.is_staff = True
    user.is_superuser = True
    user.status = User.Status.ACTIVE
    user.save(update_fields=["is_staff", "is_superuser", "status"])

Use this only for trusted administrators. A full superuser can access sensitive data, including finance and company records.

#### 3. Assign a normal user to an application role

    from authentication.models import User, Role, UserRole
    user = User.objects.get(username="manager@example.com")
    user.status = User.Status.ACTIVE
    user.save(update_fields=["status"])
    role = Role.objects.get(name="Manager")
    UserRole.objects.get_or_create(user=user, role=role)

To remove one role assignment without deleting the user:

    UserRole.objects.filter(user=user, role=role).delete()

#### 4. Create and assign module permissions

Permissions are stored separately from roles. Creating a role does not automatically give it access.

    from authentication.models import Permission, RolePermission
    permission, created = Permission.objects.get_or_create(
        permission_code="INVENTORY_READ",
        defaults={"description": "View inventory records."},
    )
    RolePermission.objects.get_or_create(role=role, permission=permission)

To give the `Admin` role all standard module permissions:

    from authentication.models import Permission, Role, RolePermission
    role = Role.objects.get(name="Admin")
    codes = [
        f"{module}_{action}"
        for module in ["INVENTORY", "FLEET", "ASSET", "FINANCE", "PROCUREMENT", "COMPANY"]
        for action in ["READ", "CREATE", "UPDATE", "DELETE"]
    ] + ["REPORTS_READ"]
    for code in codes:
        permission, _ = Permission.objects.get_or_create(
            permission_code=code,
            defaults={"description": f"{code} application permission."},
        )
        RolePermission.objects.get_or_create(role=role, permission=permission)

Run `setup_company_permissions` first if the `COMPANY_*` records do not exist. The example above safely creates any other missing permission records before assigning them.

#### 5. Remember shared endpoints

Some URLs are intentionally mapped to another module's permission set:

- Company employees and locations are readable by Fleet users because fleet assignments use them.
- Company suppliers use Procurement permissions.
- Reports require `REPORTS_READ` and financial report data additionally requires a Finance/Admin permission role.

These rules are implemented in `backend/authentication/permissions.py`. Change the mapping there if the business rule changes; changing only the frontend menu will not change API authorization.

#### 6. Apply database and login changes

After changing Python models, run:

    python manage.py makemigrations
    python manage.py migrate

Permission and role data changes normally do not require a migration because they are rows in existing tables. After changing a user or role, log out and log in again, or refresh the JWT, because the frontend may still hold an older access token. Confirm the frontend is calling the intended backend through `VITE_API_BASE_URL`.

#### 7. Diagnose a login that works but modules do not

Use the browser network panel or API client and check the response:

- `401 Unauthorized`: the JWT is missing, expired, invalid, or the frontend is calling the wrong backend.
- `403 Forbidden`: the account is authenticated but inactive or lacks the required role permission.
- `404 Not Found`: the frontend API base URL or endpoint path is incorrect.
- A successful login followed by empty dashboard sections: the user may have `REPORTS_READ` but lack the individual module `*_READ` permissions.

Verify the database connection in `.env` before changing roles. A different PostgreSQL database can contain the same username but different users, roles, and permission assignments.

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
