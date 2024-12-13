from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_babel import Babel, gettext as _
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from ldap_auth import LDAPAuth
from config import Config
import subprocess
import tempfile
import os
import secrets
import shutil
import time
import base64
from models import db, CertificateRequest
import uuid
from datetime import datetime

# Flask-App Konfiguration
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

babel = Babel(app)

# Sprachauswahl
def get_locale():
    if 'lang' in session:
        return session['lang']
    return request.accept_languages.best_match(config.LANGUAGES)

babel.init_app(app, locale_selector=get_locale)

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in config.LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# SQLAlchemy Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///certificates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

config = Config()

#User-Klasse für Flask-Login
class User(UserMixin):
    def __init__(self, username, groups=None):
        self.id = username
        self._groups = groups or []

    @property
    def groups(self):
        return self._groups

    @property
    def is_admin(self):
        return any('CN=Users,' in group for group in self.groups)

    def get_id(self):
        return self.id

    def __repr__(self):
        return f"User(id={self.id}, groups={self.groups}, is_admin={self.is_admin})"

    def to_dict(self):
        """Für die Session-Serialisierung"""
        return {
            'id': self.id,
            'groups': self._groups
        }

    @staticmethod
    def from_dict(data):
        """Aus der Session-Deserialisierung"""
        return User(data['id'], data['groups'])

# Secret Key setzen
app.secret_key = config.config['security']['secret_key']

# Flask-Login initialisieren
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    # Laden der Benutzerdaten aus der Session
    if 'user_data' not in session:
        return None
    return User.from_dict(session['user_data'])

# Login-Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        ldap_auth = LDAPAuth(config.config)
        success, error_message, groups = ldap_auth.authenticate(username, password)
        
        if success:
            user = User(username, groups)
            login_user(user)
            # Speichern der Benutzerdaten in der Session
            session['user_data'] = user.to_dict()
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error=error_message)
            
    return render_template('login.html')

# Logout-Route
@app.route('/logout')
@login_required
def logout():
    session.pop('user_data', None)  # Session-Daten löschen
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Dashboard-Startseite"""
    # Statistiken sammeln
    stats = {
        'my_requests': CertificateRequest.query.filter_by(username=current_user.id).count(),
        'pending': CertificateRequest.query.filter_by(username=current_user.id, status='pending').count(),
        'approved': CertificateRequest.query.filter_by(username=current_user.id, status='approved').count(),
        'recent_requests': CertificateRequest.query.filter_by(username=current_user.id)
                          .order_by(CertificateRequest.created_at.desc())
                          .limit(5)
                          .all()
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/request')
@login_required
def request_certificate_page():
    """Seite zur Zertifikatsbeantragung"""
    return render_template('request.html')

# Meine Anträge
@app.route('/my-requests')
@login_required
def my_requests():
    requests = CertificateRequest.query.filter_by(
        username=current_user.id
    ).order_by(CertificateRequest.created_at.desc()).all()
    return render_template('my_requests.html', requests=requests)

# Admin-Übersicht
@app.route('/admin/requests')
@login_required
def admin_requests():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    requests = CertificateRequest.query.order_by(
        CertificateRequest.created_at.desc()
    ).all()
    return render_template('admin_requests.html', requests=requests)

# Template-Abfrage
@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    """Verfügbare Zertifikatsvorlagen von ADCS abrufen"""
    try:
        print("Starte Template-Abfrage...")
        result = subprocess.run(['certutil', '-template'], 
                              capture_output=True, 
                              text=True,
                              encoding='cp1252')
        
        if result.returncode != 0:
            print("Certutil Fehler:", result.stderr)
            return jsonify([])

        templates = []
        current_template = None
        
        # Set für bereits hinzugefügte Templates
        added_templates = set()
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if line.startswith('TemplatePropCommonName ='):
                name = line.split('=')[1].strip()
                # Prüfen ob Template erlaubt und noch nicht hinzugefügt
                if config.is_template_allowed(name) and name not in added_templates:
                    current_template = {
                        'name': name,
                        'display_name': name
                    }
                    templates.append(current_template)
                    added_templates.add(name)

        return jsonify(templates)
        
    except Exception as e:
        print(f"Fehler beim Abrufen der Templates: {str(e)}")
        return jsonify([])

# Zertifikatsantrag
@app.route('/api/request', methods=['POST'])
@login_required
def request_certificate():
    """Zertifikat beantragen"""
    try:
        data = request.get_json()
        
        # Validierung der Pflichtfelder
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        
        if not name:
            raise ValueError("Name ist ein Pflichtfeld")
        if not email:
            raise ValueError("E-Mail ist ein Pflichtfeld")
        if '@' not in email or '.' not in email:
            raise ValueError("Ungültige E-Mail-Adresse")

        if config.requires_approval():
            # Speichere Antrag in der Datenbank
            cert_request = CertificateRequest(
                request_id=str(uuid.uuid4()),
                username=current_user.id,
                template=data.get('template'),
                subject=data.get('subject'),
                san_names=data.get('san_names', []),
                request_data=data,
                status='pending'
            )
            
            db.session.add(cert_request)
            db.session.commit()
            
            response = {
                'success': True,
                'message': _('Zertifikatsantrag wurde erfolgreich gespeichert und wird geprüft.'),
                'request_id': cert_request.request_id
            }
            return jsonify(response)
        
        # Wenn keine Genehmigung erforderlich, direkt Zertifikat erstellen
        result = create_certificate(data)
        return jsonify(result)

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

# Admin-Genehmigung
@app.route('/api/admin/approve/<request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    """Antrag genehmigen"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
        
    cert_request = CertificateRequest.query.filter_by(request_id=request_id).first_or_404()
    
    if cert_request.status != 'pending':
        return jsonify({'error': 'Antrag kann nicht mehr genehmigt werden'}), 400
        
    cert_request.status = 'approved'
    db.session.commit()
    
    return jsonify({'success': True})

# Admin-Ablehnung
@app.route('/api/admin/reject/<request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    """Antrag ablehnen"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
        
    cert_request = CertificateRequest.query.filter_by(request_id=request_id).first_or_404()
    
    if cert_request.status != 'pending':
        return jsonify({'error': 'Antrag kann nicht mehr abgelehnt werden'}), 400
        
    cert_request.status = 'rejected'
    db.session.commit()
    
    return jsonify({'success': True})

# Admin Request Details
@app.route('/api/admin/request-details/<request_id>')
@login_required
def get_request_details(request_id):
    """Details eines Zertifikatsantrags abrufen"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    cert_request = CertificateRequest.query.filter_by(request_id=request_id).first_or_404()
    
    return jsonify({
        'success': True,
        'request_data': cert_request.request_data
    })

# Zertifikat generieren
@app.route('/api/generate/<request_id>', methods=['POST'])
@login_required
def generate_certificate(request_id):
    """Genehmigtes Zertifikat generieren"""
    cert_request = CertificateRequest.query.filter_by(
        request_id=request_id,
        username=current_user.id,
        status='approved'
    ).first_or_404()
    
    try:
        result = create_certificate(cert_request.request_data)
        if result.get('success'):
            db.session.delete(cert_request)
            db.session.commit()
        return result
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def create_certificate(data):
    """Zertifikat erstellen"""
    try:
        # CA Server aus der Config holen
        CA_SERVER = config.get_ca_server()
        
        template_name = data.get('template')
        subject = data.get('subject')
        san_names = data.get('san_names', [])
        name = data.get('name', '')
        email = data.get('email', '')
        company = data.get('company', '')
        department = data.get('department', '')
        city = data.get('city', '')
        state = data.get('state', '')
        country = data.get('country', '')

        # Temporäre Dateien mit vollständigem Pfad
        temp_dir = tempfile.mkdtemp()
        print(f"Verwende temporäres Verzeichnis: {temp_dir}")
        
        inf_path = os.path.join(temp_dir, 'request.inf')
        req_path = os.path.join(temp_dir, 'request.req')
        cer_path = os.path.join(temp_dir, 'certificate.cer')
        pfx_path = os.path.join(temp_dir, 'certificate.pfx')

        # Distinguished Name erstellen
        subject_parts = []
        
        # Pflichtfeld CN muss zuerst kommen
        subject_parts.append(f'CN={subject}')
        
        # Optionale Felder in korrekter Reihenfolge
        if email:
            subject_parts.append(f'E={email}')
        if name:
            subject_parts.append(f'G={name}')
        if company:
            subject_parts.append(f'O={company}')
        if department:
            subject_parts.append(f'OU={department}')
        if city:
            subject_parts.append(f'L={city}')
        if state:
            subject_parts.append(f'S={state}')
        if country:
            subject_parts.append(f'C={country}')

        subject_dn = ', '.join(subject_parts)

        # INF-Datei erstellen
        inf_content = f"""[Version]
Signature="$Windows NT$"

[NewRequest]
Subject = "{subject_dn}"
KeySpec = 1
KeyLength = 2048
ProviderName = "Microsoft RSA SChannel Cryptographic Provider"
MachineKeySet = TRUE
RequestType = PKCS10
Exportable = TRUE
HashAlgorithm = sha256
KeyUsage = 0xa0

[EnhancedKeyUsageExtension]
OID = 1.3.6.1.5.5.7.3.1
OID = 1.3.6.1.5.5.7.3.2

[RequestAttributes]
CertificateTemplate = {template_name}"""

        if san_names:
            inf_content += "\nSAN = \"DNS=" + subject
            for san in san_names:
                inf_content += f"&DNS={san}"
            inf_content += '"'

        with open(inf_path, 'w', encoding='utf-8') as inf_file:
            inf_file.write(inf_content)
            
        try:
            # Erstelle Zertifikatsanforderung
            result = subprocess.run(
                ['certreq', '-new', '-f', inf_path, req_path], 
                capture_output=True, 
                text=True,
                encoding='cp1252'
            )
            if result.returncode != 0:
                raise Exception(f"Fehler bei der Anforderungserstellung: {result.stderr}")

            result = subprocess.run(
                ['certreq', '-submit', '-q', '-f', '-config', CA_SERVER, req_path], 
                capture_output=True, 
                text=True,
                encoding='cp1252'
            )
            
            # Extrahiere Request ID
            request_id = None
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                line = line.strip()
                if 'Anforderungs-ID:' in line or 'Request ID:' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        request_id = parts[1].strip().strip('"')
                        break
                elif line.isdigit():
                    request_id = line.strip()
                    break
            
            if not request_id:
                raise Exception("Keine Request ID in der Ausgabe gefunden")
                raise Exception(_("Fehler bei der Zertifikatserstellung: {}").format(result.stderr))
            
            # Warte und hole das Zertifikat
            max_attempts = 5
            for attempt in range(max_attempts):
                time.sleep(2)
                
                full_cer_path = os.path.join(os.path.abspath(temp_dir), f"{subject}.cer")
                
                result = subprocess.run(
                    ['certreq', '-retrieve', '-config', CA_SERVER, request_id, full_cer_path],
                    capture_output=True,
                    text=True,
                    encoding='cp1252'
                )
                
                if result.returncode == 0 and os.path.exists(full_cer_path):
                    if full_cer_path != cer_path:
                        shutil.copy2(full_cer_path, cer_path)
                    break

            if not os.path.exists(cer_path):
                raise Exception("Zertifikat konnte nicht erstellt werden")

            pfx_password = secrets.token_urlsafe(16)
            
            # Zertifikat in Store importieren
            result = subprocess.run(
                ['certutil', '-addstore', 'MY', cer_path],
                capture_output=True,
                text=True,
                encoding='cp1252'
            )
            
            if result.returncode != 0:
                raise Exception(f"Fehler beim Zertifikatsimport: {result.stderr}")

            # Seriennummer auslesen
            result = subprocess.run(
                ['certutil', '-dump', cer_path],
                capture_output=True,
                text=True,
                encoding='cp1252'
            )
            
            serial = None
            for line in result.stdout.split('\n'):
                if "Seriennummer:" in line:
                    serial = line.split(":", 1)[1].strip()
                    break

            if not serial:
                raise Exception("Seriennummer des Zertifikats konnte nicht ermittelt werden")

            # PFX exportieren
            result = subprocess.run(
                ['certutil', '-f', '-p', pfx_password, '-exportpfx', '-privatekey', 'MY', serial, pfx_path],
                capture_output=True,
                text=True,
                encoding='cp1252'
            )
            
            if result.returncode != 0:
                raise Exception(f"Fehler beim PFX Export: {result.stderr}")

            # Cleanup
            cleanup_result = subprocess.run(
                ['certutil', '-delstore', 'MY', serial],
                capture_output=True,
                text=True,
                encoding='cp1252'
            )

            # Dateien einlesen
            with open(cer_path, 'rb') as f:
                cert_data = f.read()
                cert_base64 = base64.b64encode(cert_data).decode('utf-8')

            with open(pfx_path, 'rb') as f:
                pfx_data = f.read()
                pfx_base64 = base64.b64encode(pfx_data).decode('utf-8')

            return {
                'success': True,
                'certificate': cert_base64,
                'pfx': pfx_base64,
                'pfx_password': pfx_password,
                'message': 'Zertifikat erfolgreich erstellt'
            }

        finally:
            # Aufräumen
            for path in [inf_path, req_path, cer_path, pfx_path]:
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e:
                        print(f"Fehler beim Löschen von {path}: {str(e)}")
            try:
                #os.rmdir(temp_dir)
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"Fehler beim Löschen des temporären Verzeichnisses: {str(e)}")

    except Exception as e:
        raise Exception(f"Fehler bei der Zertifikatserstellung: {str(e)}")

# Datenbank erstellen
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')