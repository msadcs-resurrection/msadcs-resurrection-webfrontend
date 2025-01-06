import yaml
import os
from typing import Dict, List

class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Verwende den Pfad relativ zum Skriptverzeichnis
            self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yml")
        else:
            self.config_path = config_path
        print(f"Using configuration file: {os.path.abspath(self.config_path)}")
        self.config = self._load_config()
        self.LANGUAGES = ['de', 'en']
        self.BABEL_DEFAULT_LOCALE = 'de'

    def _load_config(self) -> Dict:
        """Lädt die Konfiguration aus der YAML-Datei"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Keine Konfigurationsdatei gefunden unter {self.config_path}. "
                "Bitte kopieren Sie config.example.yml nach config.yml und passen Sie die Werte an."
            )

    def get_ca_server(self) -> str:
        """Gibt den CA-Server zurück"""
        return self.config.get('ca_server', {}).get('name', '')

    def get_allowed_templates(self) -> List[Dict]:
        """Gibt die erlaubten Templates zurück"""
        return self.config.get('certificates', {}).get('allowed_templates', [])

    def should_filter_templates(self) -> bool:
        """Prüft ob nur konfigurierte Templates angezeigt werden sollen"""
        return self.config.get('certificates', {}).get('filter_templates', True)

    def is_template_allowed(self, template_name: str) -> bool:
        """Prüft ob ein Template erlaubt ist"""
        if not self.should_filter_templates():
            return True
        return any(t['name'] == template_name for t in self.get_allowed_templates())

    def requires_approval(self) -> bool:
        """Prüft ob Zertifikatsanträge eine Admin-Genehmigung benötigen"""
        return self.config.get('security', {}).get('require_approval', True)