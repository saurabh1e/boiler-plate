
## Create User

	$ python manager.py shell
	>>> from src.user.models import User, Role, UserRole
	>>> from src.user.schemas import UserSchema, RoleSchema
	>>> data = {'email': 'test@test.com', 'password': '12345', 'username': 'testacc', 'mobile_number': '9876543211', 'first_name': 'test'}
	>>> user, error = UserSchema().load(data, session=db.session)
	>>> db.session.add(user)
	>>> db.session.commit()

Or,


	$ curl -X POST -H "Content-Type: application/json" -d '{"email": "test@test.com", "password": "12345","mobile_number": "9876543211", "first_name": "test", "username": "testacc" }' http://127.0.0.1:5000/api/v1/register/


## Get Access Token

	$ curl -X POST \ 
	-H "Content-Type: application/json" \
	-d '{ "username": "testacc", "email": "test@test.com", "password": "12345", "mobile_number": "9876543211"}' \
	http://127.0.0.1:5000/api/v1/login/  

## Using the Access Token

>Source: https://flask-jwt-extended.readthedocs.io/en/latest/basic_usage.html

	$ export ACCESS="j.w.t"
	$ curl -H "Authorization: Bearer $ACCESS" http://127.0.0.1:5000/api/v1/due

### Creating Customer 

	$ curl -X POST \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer ${ACCESS}" \
	-d '{ "username": "cus1", "email": "cus1@test.com", "password":"12345" , "mobile_number": "9871270185", "first_name": "Customer 1" }' \
	 http://127.0.0.1:5000/api/v1/customer_register/

### Verifying Customer

	$ curl -X POST \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer ${ACCESS}" \
	-d '{ "mobile_number": "9871270195", "otp": "????" }' \
	http://127.0.0.1:5000/api/v1/customer_verify/


Doubt: `src > user > views.py`, line 133, why are adding user instance to database in customer\_registraion route and not in the customer\_verify one, like in User routes ?

## Admin

1. Create a user following normal steps.
2. In the `user_role` table, add an entry for this user.id matching with role_id=1

	```bash
	$ python manager.py shell
	>>> from src.user.models import UserRole\
	>>> user = UserRole(user_id=<user_id>, role_id=1)
	>>> db.session.add(user)
	>>> db.session.commit()
	```