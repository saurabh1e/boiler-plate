from flask_security import RoleMixin, UserMixin
from sqlalchemy import UniqueConstraint, select, func, and_
from sqlalchemy.dialects.postgresql import NUMERIC, ENUM
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from src import db, ReprMixin, BaseMixin

class Due(BaseMixin, ReprMixin, db.Model):
    __repr_fields__ = ['creator', 'customer']

    invoice_num = db.Column(db.Integer, nullable=True, default=0)
    name = db.Column(db.String(20))
    amount = db.Column(NUMERIC(8, 2), nullable=False, default=0)
    transaction_type = db.Column(ENUM('fixed', 'subscription', name='varchar'), nullable=False, default='fixed')
    due_date = db.Column(db.Date, nullable=True)
    months = db.Column(db.SmallInteger, nullable=True, default=3)
    is_cancelled = db.Column(db.Boolean(), default=False)
    razor_pay_id = db.Column(db.String(20), unique=True)
    customer_id = db.Column(db.ForeignKey('user.id'), nullable=False)
    creator_id = db.Column(db.ForeignKey('user.id'), nullable=False)

    customer = db.relationship('User', uselist=False, foreign_keys=[customer_id], backref='my_dues')
    creator = db.relationship('User', uselist=False, foreign_keys=[creator_id], backref='my_payments')

    payments = db.relationship('Payment', uselist=True, lazy='dynamic', back_populates='due')

    @hybrid_property
    def is_paid(self):
        return self.transaction_type == 'fixed' and self.payments.first()

    @is_paid.expression
    def is_paid(self):
        return select([func.count(Payment.id)])\
                   .where(and_(self.transaction_type == 'fixed', Payment.due_id == self.id))\
                   .limit(1).as_scalar() > 0


class Payment(BaseMixin, ReprMixin, db.Model):
    razor_pay_id = db.Column(db.String(20))

    due_id = db.Column(db.ForeignKey('due.id'), nullable=False)

    due = db.relationship('Due', uselist=False, foreign_keys=[due_id], back_populates='payments')