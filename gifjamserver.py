import os

import User

from flask import Flask, request, make_response, redirect, url_for
from werkzeug.utils import secure_filename
from moviepy.editor import *
from flask.ext.pymongo import PyMongo, ObjectId
from uuid import uuid4
from gridfs import GridFS
from flask.ext.login import LoginManager, login_user, current_user, login_required, logout_user
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
		if login_user(user):
			return "Welcome, dude!"
		else:
			"Something weird is going on"
	else:
		return "Invalid Credentials"

@app.route("/logout", methods=["POST", "GET"])
def logout():
	logout_user()
	return redirect(url_for("index"))

@app.route("/follow/<id_to_follow>", methods=["POST"])
def follow(id_to_follow):
	if current_user.get_id() and __create_follow(current_user.get_id(), id_to_follow):
		return "You are following"
	else:
		return "You can't follow, buddy"

@app.route("/unfollow/<id_to_unfollow>", methods=["POST"])
def unfollow(id_to_unfollow):
	if current_user.get_id() and __remove_follow(current_user.get_id(), id_to_unfollow):
		return "Unfollow successful"
	else:
		return "You can't unfollow?"

def __create_follow(follower_id, id_to_follow):
	cursor = mongo.db.user.find({"_id": ObjectId(id_to_follow)})
	# check if the user we want to follow exists
	if cursor.count() == 0:
		return False
	else:
		# next we need to see if we have already followed them
		cursor = mongo.db.follow.find({"$and":[{"followed": id_to_follow}, {"follower": follower_id}]})
		if cursor.count() == 0:
			mongo.db.follow.save({"followed": id_to_follow, "follower": follower_id})
			return True
		else:
			return False

def __remove_follow(follower_id, id_to_unfollow):
	cursor = mongo.db.user.find({"_id": ObjectId(id_to_unfollow)})
	# make sure the user we want to follow exists
	if cursor.count() == 0:
		return False
	else:
		# next we need to see if we have already followed them
		cursor = mongo.db.follow.find({"$and":[{"followed": id_to_unfollow}, {"follower": follower_id}]})
		if cursor.count() == 0:
			return False
		else:
			mongo.db.follow.remove({"followed": id_to_unfollow, "follower": follower_id})
			return True

@app.route("/like/<id_to_like>", methods=["POST"])
def like(id_to_like):
	return ""

@app.route("/like/<id_to_unlike>", methods=["POST"])
def unlike(id_to_unlike):
	return ""

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
	if current_user.get_id():
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
			__insertGifInDb(basename, "", current_user.get_id())
		return ""
	else:
		return "You are not logged in."

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
		logged_in_user = params["loggedInUser"]
		if 'lastDate' in params:
			lastDate = params["lastDate"]
			gif_aggregate = []

			followers_cursor = mongo.db.follow.find({"follower": logged_in_user})
			for follow in followers_cursor:
				for gif in mongo.db.gif.find({"$and": [{"owner": follow['followed']}, {"timestamp": {"$lt": int(lastDate)}}]}).sort("timestamp")[:5]:
					gif_aggregate.append(gif)

			gif_aggregate.sort(key=lambda gif: gif['timestamp'], reverse=True)

			gif_aggregate = gif_aggregate[:5]

		else:
			# we need to build aggregate of gifs from people we are following
			gif_aggregate = []

			# we assume that user wants the latest feed content
			followers_cursor = mongo.db.follow.find({"follower": logged_in_user})
			for follow in followers_cursor:
				print follow['followed']
				for gif in mongo.db.gif.find({"owner": follow['followed']}).sort("timestamp")[:5]:
					gif_aggregate.append(gif)

			gif_aggregate.sort(key=lambda gif: gif['timestamp'], reverse=True)

			gif_aggregate = gif_aggregate[:5]

		feed = []

		# build up the dict for each gif
		for gif in gif_aggregate:
			gif_dict = {}
			gif_dict["username"] = str(mongo.db.user.find({"_id": ObjectId(gif["owner"])})[0]['email'])
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