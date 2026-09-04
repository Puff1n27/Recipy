from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ─── USER MODEL ───────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenses = db.relationship("Expense", backref="user", lazy=True)

    def to_dict(self):
        return {
            "id":       self.id,
            "username": self.username,
            "email":    self.email
        }

# ─── EXPENSE MODEL ────────────────────────────────────
class Expense(db.Model):
    __tablename__ = "expenses"

    id           = db.Column(db.Integer, primary_key=True)
    shop_name    = db.Column(db.String(255))
    date         = db.Column(db.String(50))
    total_amount = db.Column(db.Float)
    currency     = db.Column(db.String(10), default="JPY")
    category     = db.Column(db.String(100))
    notes        = db.Column(db.String(500))
    image_url    = db.Column(db.String(500))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def to_dict(self):
        return {
            "id":           self.id,
            "shop_name":    self.shop_name,
            "date":         self.date,
            "total_amount": self.total_amount,
            "currency":     self.currency,
            "category":     self.category,
            "notes":        self.notes,
            "image_url":    self.image_url,
            "created_at":   str(self.created_at),
            "updated_at":   str(self.updated_at),
            "user_id":      self.user_id
        }

    def __repr__(self):
        return f"<Expense {self.id} - {self.shop_name}>"