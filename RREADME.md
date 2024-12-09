# ADCS Web Frontend

A web-based frontend for Microsoft Active Directory Certificate Services (ADCS) that simplifies certificate request management.

## Features

- Web-based certificate request interface
- LDAP authentication and role-based access control
- Admin dashboard for certificate approval
- Multilingual interface (EN/DE)
- Configurable certificate templates
- Support for Subject Alternative Names (SAN)
- Automatic certificate creation via certreq
- Export in CER and PFX format

## System Requirements

- Python 3.7 or higher
- Windows Server with ADCS (Certificate Authority)
- LDAP/Active Directory for authentication
- certutil and certreq must be available on the system

## Installation

1. Clone or download the repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config.example.yml config.yml
```

4. Adjust configuration (see Configuration section)

5. Initialize database:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

6. Start application:
```bash
python app.py
```

## Project Structure

```
.
├── app.py                # Main application and Flask routes
├── config.py            # Configuration management
├── config.example.yml   # Example configuration
├── ldap_auth.py        # LDAP authentication
├── models.py           # Database models
├── static/             # Static assets
│   ├── css/
│   │   └── bootstrap.min.css
│   └── js/
│       ├── bootstrap.bundle.min.js
│       ├── bootstrap.min.js
│       └── jquery.min.js
└── templates/          # HTML Templates
    ├── admin_requests.html   # Admin overview
    ├── dashboard.html       # Main dashboard
    ├── login.html          # Login page
    ├── my_requests.html    # Own requests
    ├── nav.html           # Navigation
    └── request.html       # Certificate request
```

## Frontend Structure

### Templates

- `login.html`: Login form and authentication
- `nav.html`: Main navigation with language selection and user menu
- `dashboard.html`: Overview page with statistics and quick access
- `request.html`: Certificate request form
- `my_requests.html`: Overview and management of own requests
- `admin_requests.html`: Admin interface for request processing

### Assets

- Bootstrap 5.1.3 (CSS/JS)
- jQuery 3.7.1
- Custom styles and scripts in `/static`

## API Endpoints

### Public Endpoints
- `GET /login`: Login page
- `POST /login`: Perform login
- `GET /logout`: Perform logout
- `GET /set-language/<lang>`: Change language

### Authenticated Endpoints
- `GET /`: Dashboard
- `GET /request`: Certificate request form
- `GET /my-requests`: View own requests
- `POST /api/request`: Request certificate
- `GET /api/templates`: Get available certificate templates
- `POST /api/generate/<request_id>`: Generate approved certificate

### Admin Endpoints
- `GET /admin/requests`: Admin overview of all requests
- `POST /api/admin/approve/<request_id>`: Approve request
- `POST /api/admin/reject/<request_id>`: Reject request
- `GET /api/admin/request-details/<request_id>`: Get request details

## Configuration

Configuration is done via the `config.yml` file. Here are the main settings:

### CA Server Configuration
```yaml
ca_server:
  name: 'YOUR-CA-SERVER\CA-NAME'
  connection_timeout: 30
```

### Certificate Templates
```yaml
certificates:
  allowed_templates:
  - name: WebserverTLS
    allow_san: true
    enhanced_key_usage:
    - 1.3.6.1.5.5.7.3.1  # Server Authentication
    - 1.3.6.1.5.5.7.3.2  # Client Authentication
    key_specs:
    - RSA 2048
    - RSA 4096
  filter_templates: true
```

### Security
```yaml
security:
  secret_key: 'RANDOM-KEY'  # Change this to a secure key
  require_auth: false
  allowed_domains: []
```

### LDAP Configuration
```yaml
ldap:
  enabled: true
  server: "ldaps://your-domain.com"
  base_dn: "DC=your,DC=domain,DC=com"
  user_dn: "DC=your,DC=domain,DC=com"
  bind_user_dn: "cn=serviceaccount,dc=your,dc=domain,dc=com"
  bind_user_password: "your-password"
  user_search_attr: "sAMAccountName"
  groups:
    cert_admins: "CN=CertAdmins,OU=Groups,DC=your,DC=domain,DC=com"
```

## Security Notes

1. Make sure to change the `secret_key` in the configuration
2. Use HTTPS in production environments
3. Configure LDAP connection with valid certificates
4. Restrict allowed certificate templates
5. Enable approval requirement for sensitive templates
6. Set secure passwords for service accounts
7. Limit admin permissions to necessary users

## Troubleshooting

### Common Issues

1. **Certutil Errors**
   - Ensure certutil is available in the system PATH
   - Check service account permissions
   - Verify CA server configuration

2. **LDAP Connection Issues**
   - Check LDAPS URL and ports
   - Ensure certificates are valid
   - Verify service account permissions
   - Check configured group DNs

3. **Certificate Creation Errors**
   - Verify CA server configuration
   - Ensure templates are available and allowed
   - Check permissions for certificate creation
   - Validate SAN entries

## License

This project is licensed under the MIT License. See LICENSE file for details.
