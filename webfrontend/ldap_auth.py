from ldap3 import Server, Connection, Tls, SIMPLE
import ssl
from typing import Optional, Tuple

class LDAPAuth:
    def __init__(self, config):
        self.server = config.get('ldap', {}).get('server')
        self.base_dn = config.get('ldap', {}).get('base_dn')
        self.user_dn = config.get('ldap', {}).get('user_dn')
        self.bind_user_dn = config.get('ldap', {}).get('bind_user_dn')
        self.bind_user_password = config.get('ldap', {}).get('bind_user_password')
        self.user_search_attr = config.get('ldap', {}).get('user_search_attr', 'sAMAccountName')
        self.cert_admins_group = config.get('ldap', {}).get('groups', {}).get('cert_admins')
        self.cert_users_group = config.get('ldap', {}).get('groups', {}).get('cert_users')
        
        # TLS Konfiguration für LDAPS
        self.tls = Tls(validate=ssl.CERT_NONE)  # In Produktion sollten Sie Zertifikate validieren
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str], list]:
        """
        Authentifiziert einen Benutzer gegen LDAP und prüft Gruppenzugehörigkeit
        
        Returns:
            Tuple(is_authenticated: bool, error_message: Optional[str], groups: list)
        """
        try:
            # Server-Verbindung aufbauen
            server = Server(self.server, use_ssl=True, tls=self.tls)
            
            # Erste Verbindung mit Service-Account
            with Connection(server, user=self.bind_user_dn, password=self.bind_user_password) as service_conn:
                if not service_conn.bind():
                    return False, "Service account binding failed", []
                
                # Benutzer in LDAP suchen
                search_filter = f"({self.user_search_attr}={username})"
                
                success = service_conn.search(
                    self.base_dn, 
                    search_filter, 
                    attributes=['distinguishedName', 'memberOf']
                )
                
                if not success:
                    return False, "User not found", []
                
                if not service_conn.entries:
                    return False, "User not found", []
                
                user_dn = service_conn.entries[0].distinguishedName.value
                
                # Benutzerauthentifizierung
                with Connection(server, user=user_dn, password=password) as user_conn:
                    if not user_conn.bind():
                        return False, "Invalid credentials", []
                    
                    # Gruppenmitgliedschaften prüfen
                    groups = []
                    if hasattr(service_conn.entries[0], 'memberOf'):
                        groups = [str(group) for group in service_conn.entries[0].memberOf]
                    
                    return True, None, groups
                    
        except Exception as e:
            return False, f"Authentication error: {str(e)}", []