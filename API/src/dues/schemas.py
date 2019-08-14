from src import ma, BaseSchema
from .models import Due, Payment


class DueSchema(BaseSchema):
    class Meta:
        model = Due
        exclude = ('updated_on', 'creator_id')

    id = ma.Integer(dump_only=True)
    amount = ma.Integer(required=True)
    transaction_type = ma.String(required=True)
    due_date = ma.Date(required=False)

    customer_id = ma.Integer(load_only=True, allow_one=False)

    customer = ma.Nested('UserSchema', many=False, dump_only=True, only=('id', 'first_name', 'mobile_number'))
    creator = ma.Nested('UserSchema', many=False, dump_only=True, only=('id', 'first_name', 'mobile_number'))


class PaymentSchema(BaseSchema):
    class Meta:
        model = Payment
        exclude = ('updated_on', )

    due_id = ma.Integer(load_only=True)
    razorpay_id = ma.String(load=True)

    due = ma.Nested('DueSchema', many=True, dump_only=True, only=('id', 'amount', 'transaction_type'))

