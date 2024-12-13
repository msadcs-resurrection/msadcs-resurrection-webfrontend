from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

db = SQLAlchemy()

class CertificateRequest(db.Model):
    __tablename__ = 'certificate_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.String(50), unique=True)
    username = db.Column(db.String(100), nullable=False)
    template = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    san_names = db.Column(db.JSON)
    request_data = db.Column(db.JSON)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'template': self.template,
            'subject': self.subject,
            'san_names': self.san_names,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }