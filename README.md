# MS ADCS Web Frontend

A web frontend for Microsoft Active Directory Certificate Services (ADCS) that provides a user-friendly state of the art interface for requesting and managing certificates.

## Intention

MS ADCS is slowly dying, there appears to be no further development. The web interface certsrv is now only cumbersome to access and has no modern features whatsoever, a REST API for automation is non-existent, ACME only works through workarounds. Nevertheless, the system does its job excellently, is easy to use, and anyone who has looked at other CA systems will find that the alternatives aren't perfect either.
For this reason, I started the MSADCS-Resurrection project, which aims to bring the MS CA back to a state that can absolutely compete with other modern CA systems today and is also fit for the future ahead.

## Features

- LDAP/AD Authentication
- Certificate request workflow with approval process
- Admin interface for managing certificate requests
- Multilingual interface (EN/DE)
- Email notifications comming soon...
- Integration with Microsoft ADCS
- Support for SQL databases (PostgreSQL) comming soon...

## Screenshots



## Prerequisites

- Python 3.8 or higher
- Microsoft Active Directory Certificate Services
- PostgreSQL database (later...)
- SMTP server for notifications (later...)
- Windows environment with certutil.exe

## Installation

1. Clone the repository
```bash
git clone [repository-url]
cd adcs-webfrontend
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
venv\Scripts\activate     # On Windows
```

3. Install required packages
```bash
pip install -r requirements.txt
```

4. Create config.yml (use config.example.yml as template)
```yaml
ca_server:
  connection_timeout: 30
  name: "your-ca-server"

database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  name: "certmanager"
  user: "dbuser"
  password: "dbpassword"

smtp:
  host: "smtp.your-domain.com"
  port: 25
  use_tls: false
  username: ""
  password: ""
  from_address: "noreply@your-domain.com"
  admin_notification:
    - "admin@your-domain.com"

ldap:
  enabled: true
  server: "ldaps://your-domain.com"
  base_dn: "DC=your,DC=domain,DC=com"
  user_dn: "DC=your,DC=domain,DC=com"
  bind_user_dn: "cn=service-account,ou=Users,dc=your,dc=domain,dc=com"
  bind_user_password: "service-account-password"
  user_search_attr: "sAMAccountName"
  groups:
    cert_admins: "CN=CertAdmins,OU=Groups,DC=your,DC=domain,DC=com"
```

## Configuration

1. Database Setup
```bash
# Create PostgreSQL database and user
psql -U postgres
CREATE DATABASE certmanager;
CREATE USER certuser WITH ENCRYPTED PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE certmanager TO certuser;
```

2. Initialize the database
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

3. Compile translations
```bash
pybabel compile -d translations
```

## Usage

1. Start the application
```bash
python app.py
```

2. Access the web interface at http://localhost:5000

## Security Considerations

- Run behind a reverse proxy with SSL/TLS enabled
- Use strong passwords for service accounts
- Regularly review access logs and certificate requests
- Keep the system and all dependencies up to date
- Backup the database regularly

## Development

1. Update translations
```bash
# Extract new strings
pybabel extract -F babel.cfg -o messages.pot .

# Update translation files
pybabel update -i messages.pot -d translations

# Compile translations
pybabel compile -d translations
```

2. Running tests (coming soon)
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask and its extensions
- Microsoft Active Directory Certificate Services
- Bootstrap for the UI components

## Support

For support, please open an issue in the GitHub repository.
