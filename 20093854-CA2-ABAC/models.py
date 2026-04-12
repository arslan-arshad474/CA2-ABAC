from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

import pytz

db = SQLAlchemy()

def get_ireland_time():
    return datetime.now(pytz.timezone('Europe/Dublin'))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50))
    access_required = db.Column(db.String(100))
    location = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(50))
    payroll = db.Column(db.String(50))
    password = db.Column(db.String(255), nullable=True)
    password_token = db.Column(db.String(100), nullable=True)
    is_first_login = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    
    role = db.Column(db.String(10), default='User') # 'User' or 'Admin'
    
    # ABAC Monitoring fields
    failed_attempts = db.Column(db.Integer, default=0)
    is_locked = db.Column(db.Boolean, default=False)
    lockout_timestamp = db.Column(db.DateTime, nullable=True)
    force_logout = db.Column(db.Boolean, default=False)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    device = db.Column(db.String(255))
    location = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=get_ireland_time)
    
    user = db.relationship('User', backref=db.backref('activities', lazy=True))
