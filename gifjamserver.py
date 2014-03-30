import os

import User

from flask import Flask, request, make_response, redirect, url_for
from werkzeug.utils import secure_filename
from moviepy.editor import *
from flask.ext.pymongo import PyMongo, ObjectId
from uuid import uuid4
from gridfs import GridFS
from flask.ext.login import LoginManager, login_user, current_user, login_required
from flask.ext.bcrypt import Bcrypt
import time
import json

UPLOAD_FOLDER = 'file-uploads'
ALLOWED_EXTENSIONS = set(['mp4'])
HOSTNAME = "128.239.163.254:5000"
DEBUG = True

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'this needs to be secret!'

mongo = PyMongo(app)

flask_bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)

def allowed_file(filename):
	"""Takes in a filename and returns whether or not it is of the allowed filetype."""
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(userid):
	user = User.User()
	user.load_by_id(userid)
	if user.is_real():
		return user
	else:
		return None

@app.route("/register", methods=["POST"])
def register():
	email = request.form['email']
	password_hash = flask_bcrypt.generate_password_hash(request.form['password'])
	user = User.User(email,password_hash)
	user.save()
	return ""

@app.route("/login", methods=["POST"])
def login():
	email = request.form['email']
	
	user = User.User(email, request.form['password'])

	if user.authenticate():
		login_user(user)
		return "Welcome, email!"
	else:
		return "Invalid Credentials"

@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect(url_for("index"))

@app.route("/")
def index():
	return "Hello Tribe Hacks!"

@app.route("/file/<filename>")
def get_file(filename):
	# Check to see if the file exists
	cursor = mongo.db.fs.files.find({"filename": filename})
	if cursor.count() == 0:
		return "File not found"
	else:
		# retrieve the mongo object id
		gridfs_id = cursor[0]["_id"]

		# get our grid fs instance
		fs = GridFS(mongo.db)

		# serve the file
		file = fs.get(ObjectId(gridfs_id))
		response = make_response(file.read())
		response.mimetype = file.content_type
		return response

@app.route("/upload", methods=["POST"])
def upload():
	file = request.files['video']

	if file and allowed_file(file.filename):
		# escape the filename so it is safe to store on the server
		basename = str(uuid4())
		filename = secure_filename(basename + ".mp4")

		# save the uploaded video.
		name_with_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
		file.save(name_with_path)

		gifname = filename.rsplit(".", 1)[0] + ".gif"
		gifpath = "converted/" + gifname

		# Create the gif
		VideoFileClip(name_with_path).subclip((0,0.0),(0,5.0)).resize(0.3).to_gif(gifpath)

		# save the video and gif to mongo
		mp4file = open(name_with_path)
		giffile = open(gifpath)
		mongo.save_file(filename, mp4file)
		mongo.save_file(gifname, giffile)
		giffile.close()

		# clean up what we uploaded.
		os.remove(name_with_path)
		os.remove(gifpath)

		# finally, add an entry in the gif database
		__insertGifInDb(basename, "", __getUserOid("root"))
	return ""

def __getUserOid(name):
	"""Looks up username in database and returns the oid of that user"""
	cursor = mongo.db.user.find({"name": name})

	if cursor.count() == 0:
		return None
	else:
		return cursor[0]["_id"]

def __insertGifInDb(name, caption, owner_oid):
	"""Inserts the gif into the db"""
	mongo.db.gif.insert({"name": name, "caption":caption, "owner":owner_oid, "timestamp":int(time.time())})

@app.route("/profile_feed")
def profile_feed():
	"""Takes in a lastDate and user GET variables. Returns the next food in the feed"""
	params = request.args
	if 'user' in params:
		username = params['user']
		if 'lastDate' in params:
			lastDate = params["lastDate"]
			recent_cursor = mongo.db.gif.find({"$and":[{"owner": __getUserOid(username)},{"timestamp": {"$lt": int(lastDate)}}]}).sort("timestamp")[:5]
		else:
			# assume that we want the most recent
			# sort the elements in the cursor by timestamp
			# get the top 5 elements
			recent_cursor = mongo.db.gif.find({"owner": __getUserOid(username)}).sort("timestamp")[:5]

		feed = []

		# build up the dict for each gif
		for gif in recent_cursor:
			gif_dict = {}
			gif_dict["username"] = username
			gif_dict["caption"] = gif["caption"]
			gif_dict["timestamp"] = gif["timestamp"]
			gif_dict["gif_url"] = "http://" + HOSTNAME + "/file/" + gif["name"] + ".gif"
			gif_dict["likes"] = []
			gif_dict["comments"] = []

			feed.append(gif_dict)

		return json.dumps(feed)
	else:
		return "A user needs to be specified"

@app.route("/news_feed")
def news_feed():
	"""Takes in a lastDate and a loggedInUser"""
	params = request.args
	if 'loggedInUser' in params:
		logged_in_user = params["logged_in_user"]
		if 'lastDate' in params:
			lastDate = params["lastDate"]
			recent_cursor = []
		else:
			# we assume that user wants the latest feed content
			recent_cursor = []

		feed = []

		# build up the dict for each gif
		for gif in recent_cursor:
			gif_dict = {}
			gif_dict["username"] = username
			gif_dict["caption"] = gif["caption"]
			gif_dict["timestamp"] = gif["timestamp"]
			gif_dict["gif_url"] = "http://" + HOSTNAME + "/file/" + gif["name"] + ".gif"
			gif_dict["likes"] = []
			gif_dict["comments"] = []

			feed.append(gif_dict)

		return json.dumps(feed)
	else:
		return "You are not logged in"

if __name__ == "__main__":
	if DEBUG:
		app.run(host="0.0.0.0", debug=True)
	else:
		app.run(host="0.0.0.0")