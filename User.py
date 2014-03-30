from gifjamserver import mongo, flask_bcrypt, ObjectId

class User():
	def __init__(self, email=None, password=None, active=True, id=None, authenticated=False):
		self.email = email
		self.password = password
		self.active = active
		self.id = None
		self.authenticated = False;

	def load_by_id(self, id):
		cursor = mongo.db.user.find({"_id": ObjectId(id)})
		if cursor.count() == 0:
			return None
		else:
			user_from_db = cursor[0]
			self.email = user_from_db['email']
			self.password = user_from_db['password']
			self.active = user_from_db['active']
			self.id = str(user_from_db['_id'])
			return self

	def is_real(self):
		if self.id is None:
			return False
		else:
			return True

	def authenticate(self):
		cursor = mongo.db.user.find({"$and":[{"email": self.email}]})
		if cursor.count() == 0:
			return False
		else:
			if flask_bcrypt.check_password_hash(cursor[0]['password'], self.password):
				self.load_by_id(cursor[0]['_id'])
				self.authenticated = True
				return True
			else:
				return False

	def is_active(self):
		return self.active is not None

	def get_id(self):
		return self.id

	def is_authenticated(self):
		return self.authenticated

	def is_anonymous(self):
		return False

	def save(self):
		if self.id is None:
			mongo.db.user.save({"email": self.email, "password": self.password, "active": self.active})	
		else:
			mongo.db.user.save({"_id": self.id, "email": self.email, "password": self.password, "active": self.active})

