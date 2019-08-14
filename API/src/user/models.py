from flask_login import current_user
from flask_security import RoleMixin, UserMixin
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from src import db, ReprMixin, BaseMixin
from datetime import datetime


class UserRole(BaseMixin, db.Model):
    user_id = db.Column(db.ForeignKey('user.id', ondelete='CASCADE'), index=True)
    role_id = db.Column(db.ForeignKey('role.id', ondelete='CASCADE'), index=True)

    user = db.relationship('User', foreign_keys=[user_id])
    role = db.relationship('Role', foreign_keys=[role_id])

    UniqueConstraint(user_id, role_id)


class Role(BaseMixin, RoleMixin, ReprMixin, db.Model):
    name = db.Column(db.String(80), unique=True, index=True)
    description = db.Column(db.String(255))
    is_hidden = db.Column(db.Boolean(), default=False, index=True)

    users = db.relationship('User', back_populates='roles', secondary='user_role')


class User(BaseMixin, ReprMixin, UserMixin, db.Model):
    __repr_fields__ = ['id', 'first_name']

    razor_pay_id = db.Column(db.String(20), nullable=True, unique=True)
    email = db.Column(db.String(127), unique=True, nullable=True, index=True)
    password = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(55), nullable=False)
    last_name = db.Column(db.String(55), nullable=True)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    business_name = db.Column(db.String(55), nullable=True)
    counter = db.Column(db.Integer, nullable=True, default=0)

    picture = db.Column(db.Text(), nullable=True, index=True)
    active = db.Column(db.Boolean(), default=False)
    confirmed_at = db.Column(db.DateTime(), default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())

    last_login_ip = db.Column(db.String(45))
    current_login_ip = db.Column(db.String(45))
    login_count = db.Column(db.Integer)

    roles = db.relationship('Role', back_populates='users', secondary='user_role')

    @hybrid_property
    def fixed_dues(self):
        from src.dues.models import Due
        return Due.query.with_entities(Due.amount)\
            .filter(Due.is_paid.isnot(True), Due.creator.creator_id == current_user.id, Due.is_cancelled.isnot(True),
                    Due.transaction_type == 'fixed',
                    Due.customer_id == self.id).limit(1).scalar()

    @hybrid_property
    def subscriptions(self):
        from src.dues.models import Due
        return Due.query.with_entities(func.count(Due.id)) \
            .filter(Due.creator_id == current_user.id, Due.is_cancelled.isnot(True),
                    Due.transaction_type == 'subscription',
                    Due.customer_id == self.id).limit(1).scalar()


class UserToUser(BaseMixin, ReprMixin, db.Model):
    business_owner_id = db.Column(db.ForeignKey('user.id'), nullable=False)
    customer_id = db.Column(db.ForeignKey('user.id'), nullable=False)

    UniqueConstraint(business_owner_id, customer_id)
