from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'headman', 'student'
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))  # Новая связь со студентом

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    cmk = db.Column(db.String(100), nullable=False)  # ЦМК
    students = db.relationship('Student', backref='group', lazy=True)
    users = db.relationship('User', backref='group', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    user = db.relationship('User', backref='student_ref', uselist=False)  # Обратная связь

class Supervisor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    subjects = db.Column(db.Text)  # CSV список предметов
    topics = db.relationship('Topic', backref='supervisor', lazy=True)

class WorkType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 'курсовая', 'дипломная'
    subject = db.Column(db.String(100), nullable=False)
    topics = db.relationship('Topic', backref='work_type', lazy=True)

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='free')  # 'free', 'reserved', 'assigned'
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisor.id'), nullable=False)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_type.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=True)
    reserved_at = db.Column(db.DateTime)
    reserved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Явно указываем связь с student
    student = db.relationship('Student', backref='assigned_topic', foreign_keys=[student_id])

class TopicReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    reserved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reserved_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    topic = db.relationship('Topic', backref='reservations')
    group = db.relationship('Group')
    user = db.relationship('User')