from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.dialects.postgresql import JSON  # Use this for PostgreSQL
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_feedback = db.Column(db.String(1500), nullable=True)
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(1500))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Supervisor_Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(1500))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Info(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group = db.Column(db.Integer) #integer to store cadet group
    squadron = db.Column(db.Integer) #integer to store cadet squadron
    flight = db.Column(db.String(20)) #string to store cadet flight
    class_year = db.Column(db.Integer) # integer to store class year
    admin = db.Column(db.Integer) #integer to store squadron/group/wing admin right
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) #uses foreign key to connect to user

class Stratification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    overall_elo = db.Column(db.Integer)
    duty_perform_elo = db.Column(db.Integer)
    professionalism_elo = db.Column(db.Integer)
    leadership_elo = db.Column(db.Integer)
    character_elo = db.Column(db.Integer)
    num_comparisons = db.Column(db.Integer, default=0) #used to balance user comparisons
    comparison_history = db.Column(JSON, default=list)  # New field to track comparisons
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Performance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    overall_score = db.Column(db.Integer, default=0)
    question_1 = db.Column(db.Integer, default=0)
    question_1_total = db.Column(db.Integer, default=0)
    question_2 = db.Column(db.Integer, default=0)
    question_3 = db.Column(db.Integer, default=0)
    question_4 = db.Column(db.Integer, default=0)
    question_5 = db.Column(db.Integer, default=0)
    question_6 = db.Column(db.Integer, default=0)
    question_7 = db.Column(db.Integer, default=0)
    question_8 = db.Column(db.Integer, default=0)
    question_9 = db.Column(db.Integer, default=0)
    question_10 = db.Column(db.Integer, default=0)
    num_squad_comparisons = db.Column(db.Integer, default = 0)
    staff_comparison_history = db.Column(MutableList.as_mutable(JSON), default=list)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    notes = db.relationship('Note')
    supervisor_notes = db.relationship('Supervisor_Notes')
    feedback = db.relationship('Feedback')
    stratification = db.relationship('Stratification')
    info = db.relationship('Info')