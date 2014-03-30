from gifjam-server import mongo

class User():
  def __init__(self, email=None, password=None, active=True, id=None):
    self.email = email
    self.password = password
    self.active = active
    self.id = None

  def load_by_id(self, id):
  	cursor = mongo.db.user.find({"_id": id})
  	if cursor.count() == 0:
			return None
		else:
			user_from_db = cursor[0]
			self.email = user_from_db['email']
			self.password = user_from_db['password']
			self.active = user_from_db['active']
			self.id = user_from_db['_id']
			return self

	def is_real(self):
		if self.id is None:
			return False
		else:
			return True

	def save(self):
		mongo.db.user.save({"_id": self.id, "email": self.email, "password": self.password, "active": self.active})