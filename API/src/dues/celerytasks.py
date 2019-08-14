''' Celery Tasks '''

from src import db, razor as razorpay, sms, celery, url_shortener
from .schemas import Due

# Send reminder on due-date
@celery.task(name="celery.sms_on_due_date")
def sms_on_due_date(obj_id):
    dueObj = Due.query.get(obj_id)

    # Only execute if payment is not done
    if dueObj.due_date is not None:

        content= [dict(
        message=f'3 days remaining of your {dueObj.creator.business_name} subscription! Pay now.',
        to=[dueObj.customer.mobile_number]
        )]

        sms.send_sms(content=content)

# Send reminder 3 dasy before due-date
@celery.task(name="celery.sms_before_3_days")
def sms_before_3_days(obj_id):
    dueObj = Due.query.get(obj_id)

    # Only execute if payment is not done
    if dueObj.due_date is not None:

        content= [dict(
            message=f'Failure to pay today will result in halt of your {dueObj.creator.business_name} service! Pay Now!',
            to=[dueObj.customer.mobile_number]
            )]

        sms.send_sms(content=content)

    #dueObj.due_date = None if payment is successful


# Send invoice after payment
@celery.task(name="celery.send_invoice")
def send_invoice(invoice_url, obj_id):
    dueObj = Due.query.get(obj_id)
    content = [dict(message=f'Thank you for your interest in the service provided by'
            f' {dueObj.creator.business_name}. Here\'s your invoice and enjoy the service.\n'
            f' Invoice --> \n {invoice_url}', to=[dueObj.customer.mobile_number])]
            
    sms.send_sms(content=content)

@celery.task(name="celery.do_payment")
def do_payment(obj_id):
    obj = Due.query.get(obj_id)
    if obj.customer.razor_pay_id:
        customer = razorpay.customer.fetch(customer_id=obj.customer.razor_pay_id)
    else:
        customer = razorpay.customer.create(
            data={'name': obj.customer.first_name, 'contact': obj.customer.mobile_number})
        obj.customer.razor_pay_id = customer['id']
        db.session.commit()
    print(customer)
    
    if obj.transaction_type == 'subscription':
        plan = razorpay.plan.create(data={
            "period": "monthly",
            "interval": 1,
            "item": {
                "name": obj.name,
                "description": obj.name,
                "amount": float(obj.amount) * 100,
                "currency": "INR"
            }
        })
        import time
        timestamp = time.mktime(obj.due_date.timetuple())
        data = dict(plan_id=plan['id'], total_count=obj.months, customer_notify=1, customer_id=customer['id'],
                    start_at=timestamp)
        subscription = razorpay.subscription.create(data=data)
        obj.razor_pay_id = subscription['id']
        db.session.commit()
        print(subscription)
        token = subscription['id']
        payment_url = f'http://localhost:8000/do_payment.html?token={token}'
        print(payment_url)
        content = [dict(message=f'Thank you for your interest in the service provided by'
        f' {obj.creator.business_name}.Please complete your subscription and enjoy the service.'
        f' Click to pay--> {payment_url}', to=[obj.customer.mobile_number])]
        sms.send_sms(content=content)

        #send_invoice.delay(, obj_id)

    else:
        inv = razorpay.invoice.create(data={
            "customer": {
                "name": obj.customer.first_name,
                "email": "",
                "contact": obj.customer.mobile_number
            },
            "type": "link",
            "view_less": 1,
            "amount": float(obj.amount) * 100,
            "currency": "INR",
            "description": obj.name,
        })

        context = { 
            "inv_id": inv['id'],
            "order_id": inv['order_id']
        }

        send_invoice.delay(inv, obj_id)
