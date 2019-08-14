from flask_security import current_user
from sqlalchemy import and_

from src import db
from src.user.models import UserToUser
from src.utils import ModelResource, operators as ops
from .schemas import Due, DueSchema, Payment, PaymentSchema

from src.dues.celerytasks import sms_on_due_date, sms_before_3_days, send_invoice, do_payment

class DueResource(ModelResource):
    model = Due
    schema = DueSchema

    auth_required = True

    # roles_accepted = ('admin', 'business_owner', 'customer')

    exclude = ()

    filters = {
        'id': [ops.Equal, ops.In],
        'creator_id': [ops.Equal, ops.In],
        'customer_id': [ops.Equal, ops.In],
        'transaction_type': [ops.Equal, ops.In],
        'created_on': [ops.DateTimeEqual, ops.DateTimeLesserEqual, ops.DateTimeGreaterEqual],
        'due_date': [ops.DateTimeEqual, ops.DateTimeLesserEqual, ops.DateTimeGreaterEqual],
        'is_paid': [ops.Boolean],
        'is_cancelled': [ops.Boolean]

    }

    order_by = ['created_on', 'id', 'due_date']

    only = ()

    def has_read_permission(self, qs):
        return qs.filter(Due.creator_id == current_user.id)

    def has_change_permission(self, obj):

        if obj.creator_id == current_user.id and \
                db.session.query(UserToUser.query.filter(UserToUser.business_owner_id == current_user,
                                                         UserToUser.customer_id == obj.customer_id).exists()) \
                        .scalar():
            return True
        return False

    def has_delete_permission(self, obj):
        return False

    def has_add_permission(self, objects):
        for obj in objects:
            obj.creator_id = current_user.id
            if not db.session.query(UserToUser.query.filter(UserToUser.business_owner_id == current_user.id,
                                                            UserToUser.customer_id == obj.customer_id).exists()) \
                    .scalar():
                return False
        return True

    def after_objects_save(self, objects):
        for obj in objects:
            current_user.counter += 1
            obj.invoice_num = current_user.counter

            # Celery tasks executions
            try:
                do_payment.delay(obj.id)
                if obj.transaction_type == 'subscription':
                    from datetime import timedelta
                    sms_before_3_days.apply_async(args=[obj.id], eta=obj.due_date-timedelta(days=3))
                    sms_on_due_date.apply_async(args=[obj.id], eta=obj.due_date)
                elif obj.transaction_type == 'fixed':
                    obj.due_date = None 

            except Exception as e:
                print("Couldn't complete transaction:", e)

            db.session.commit()


class PaymentResource(ModelResource):
    model = Payment
    schema = PaymentSchema

    auth_required = True

    exclude = ()

    filters = {
        'id': [ops.Equal, ops.In],
        'razorpay_id': [ops.Equal, ops.In],
        'due_id': [ops.Equal, ops.In],
        'created_on': [ops.DateTimeEqual, ops.DateTimeLesserEqual, ops.DateTimeGreaterEqual],
    }

    order_by = ['created_on', 'id', 'due_id']

    only = ()

    def has_read_permission(self, qs):
        return qs.join(Due, and_(Due.id == Payment.due_id)).filter(Due.creator_id == current_user.id)

    def has_change_permission(self, obj):
        return False

    def has_delete_permission(self, obj):
        return False

    def has_add_permission(self, objects):
        return False
