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
CHUNK_SIZE = 50
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
	username = request.form['username']
	password_hash = flask_bcrypt.generate_password_hash(request.form['password'])
	user = User.User(username,password_hash)
	user.save()
	return ""

@app.route("/login", methods=["POST"])
def login():
	username = request.form['username']
	
	user = User.User(username, request.form['password'])

	if user.authenticate():
		if login_user(user):
			return user.get_id()
		else:
			"null"
	else:
		return "null"

@app.route("/logout", methods=["POST", "GET"])
def logout():
	logout_user()
	return redirect(url_for("index"))

@app.route("/follow/<user_id>", methods=["POST"])
def follow(user_id):
	id_to_follow = request.form['id_to_follow']
	if __create_follow(user_id, id_to_follow):
		return "You are following"
	else:
		return "You can't follow, buddy"

@app.route("/unfollow/<user_id>", methods=["POST"])
def unfollow(user_id):
	id_to_unfollow = request.form['id_to_unfollow']
	if __remove_follow(user_id, id_to_unfollow):
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

@app.route("/like/<user_id>", methods=["POST"])
def like(user_id):
	gif_name = request.form['gif_name']
	if __create_like(user_id, gif_name):
		return "Like successful"
	else:
		return "You can't Like!"

def __create_like(liker_id, gif_name):
	cursor = mongo.db.user.find({"_id": ObjectId(liker_id)})
	# check if the liker exists
	if cursor.count() == 0:
		return False
	else:
		# next we need to see if the gif exists
		cursor = mongo.db.gif.find({"name": gif_name})
		if cursor.count() == 0:
			return False
		else:
			# check to see that the combination exists
			cursor = mongo.db.like.find({"$and":[{"liker": liker_id}, {"name": gif_name}]})
			if cursor.count() == 0:
				mongo.db.like.save({"liker": liker_id, "name": gif_name})
				return True
			else:
				return False

@app.route("/unlike/<user_id>", methods=["POST"])
def unlike(user_id):
	gif_name = request.form['gif_name']
	if __remove_like(user_id, gif_name):
		return "Unlike successful"
	else:
		return "You can't unlike?"

def __remove_like(liker_id, gif_name):
	cursor = mongo.db.user.find({"_id": ObjectId(liker_id)})
	# check if the liker exists
	if cursor.count() == 0:
		return False
	else:
		# next we need to see if the gif exists
		cursor = mongo.db.gif.find({"name": gif_name})
		if cursor.count() == 0:
			return False
		else:
			gif_id = cursor[0]["_id"]
			# check to see that the combination exists
			cursor = mongo.db.like.find({"$and":[{"liker": liker_id}, {"gif_id": gif_id}]})
			if cursor.count() == 0:
				return False
			else:
				mongo.db.like.remove({"liker": liker_id, "gif_id": gif_id})
				return True

@app.route("/update_profile/<user_id>", methods=["POST"])
def update_profile(user_id):
	params = request.form
	if "bio" in params:
		bio = request.form['bio']
		user = User.User()
		user.load_by_id(user_id)
		user.update_profile(bio=bio)
	
	if "profile_gif" in params:
		profile_gif = request.form['profile_gif']
		user = User.User()
		user.load_by_id(user_id)
		user.update_profile(profile_gif=profile_gif)
	return "Update Successful"

@app.route("/get_profile/<user_id>")
def get_profile(user_id):
	returnDict = {}
	user = mongo.db.user.find({"_id":ObjectId(user_id)})[0]
	returnDict['bio'] = user['bio']
	if user['profile_gif'] is None:
		returnDict['profile_gif_url'] = ""
	else:	
		returnDict['profile_gif_url'] = "http://" + HOSTNAME + "/file/" + str(user['profile_gif']) + ".gif"
	returnDict['username'] = user['username']

	# get following
	params = request.args
	if "viewer_id" in params:
		my_user = params["viewer_id"]
		following_cursor = mongo.db.follow.find({"$and":[{"follower": my_user}, {"followed": user_id}]})
		returnDict['is_following'] = following_cursor.count() > 0

	return json.dumps(returnDict)

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

@app.route("/upload/<user_id>", methods=["POST"])
def upload(user_id):
	# if current_user.get_id():
	file = request.files['video']

	if "caption" in request.form:
		caption = request.form['caption']
	else:
		caption = ""

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
		clip = vfx.rotation(VideoFileClip(name_with_path).resize(0.75), -90)
		clip.crop(x1=0,y1=0,x2=clip.w,y2=clip.w-clip.h).to_gif(gifpath)

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
		__insertGifInDb(basename, caption, user_id)
		# __insertGifInDb(basename, "", current_user.get_id())
		# __insertGifInDb(basename, "", "")

		return "Upload successful"
	else:
		return "That type of file is not allowed"
	# else:
	# 	return "You are not logged in."

@app.route("/upload/profile_gif/<user_id>", methods=["POST"])
def upload_for_profile_gif(user_id):
	# if current_user.get_id():
	file = request.files['video']

	if "caption" in request.form:
		caption = request.form['caption']
	else:
		caption = ""

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
		clip = vfx.rotation(VideoFileClip(name_with_path).resize(0.75), -90)
		clip.crop(x1=0,y1=0,x2=clip.w,y2=clip.w-clip.h).to_gif(gifpath)

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
		__insertGifInDb(basename, caption, user_id)
		# __insertGifInDb(basename, "", current_user.get_id())
		# __insertGifInDb(basename, "", "")

		user = User.User()
		user.load_by_id(user_id)
		user.update_profile(profile_gif=filename.rsplit(".", 1)[0])

		return "Upload successful"
	else:
		return "That type of file is not allowed"
	# else:
	# 	return "You are not logged in."

def __getUserOid(name):
	"""Looks up username in database and returns the oid of that user"""
	cursor = mongo.db.user.find({"username": name})

	if cursor.count() == 0:
		return None
	else:
		return cursor[0]["_id"]

def __getUsername(oid):
	cursor = mongo.db.user.find({"_id": ObjectId(oid)})

	if cursor.count() == 0:
		return None
	else:
		return cursor[0]["username"]

def __insertGifInDb(name, caption, owner_oid):
	"""Inserts the gif into the db"""
	mongo.db.gif.insert({"name": name, "caption":caption, "owner":owner_oid, "timestamp":int(time.time())})

@app.route("/profile_feed")
def profile_feed():
	"""Takes in a lastDate and user GET variables. Returns the next food in the feed"""
	params = request.args
	if 'user' in params:
		user_id = params['user']
		if 'lastDate' in params:
			lastDate = params["lastDate"]
			recent_cursor = mongo.db.gif.find({"$and":[{"owner": user_id},{"timestamp": {"$lt": int(lastDate)}}]}).sort("timestamp", -1)[:CHUNK_SIZE]
		else:
			# assume that we want the most recent
			# sort the elements in the cursor by timestamp
			# get the top 5 elements
			recent_cursor = mongo.db.gif.find({"owner": user_id}).sort("timestamp", -1)[:CHUNK_SIZE]

		feed = []

		# build up the dict for each gif
		for gif in recent_cursor:
			gif_dict = {}
			gif_dict["username"] = mongo.db.user.find({"_id": ObjectId(user_id)})[0]['username']
			gif_dict["user_id"] = user_id
			gif_dict["caption"] = gif["caption"]
			gif_dict["timestamp"] = gif["timestamp"]
			gif_dict["gif_url"] = "http://" + HOSTNAME + "/file/" + gif["name"] + ".gif"
			gif_dict["likes"] = __get_likes(gif["name"])
			gif_dict["comments"] = []

			feed.append(gif_dict)

		return json.dumps(feed)
	else:
		return "A user needs to be specified"

def __get_likes(gif_name):
	returnList = []
	for like in mongo.db.like.find({"name": gif_name}):
		returnList.append(__getUsername(like['liker']))
	return returnList

@app.route("/api/user_exists")
def user_exists():
	params = request.args
	if 'username' in params:
		username = params['username']
		user_id = __getUserOid(username)
		if user_id:
			return str(user_id)
		else:
			return ""
	else:
		return "You need to provide a username"

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
				for gif in mongo.db.gif.find({"$and": [{"owner": follow['followed']}, {"timestamp": {"$lt": int(lastDate)}}]}).sort("timestamp", -1)[:CHUNK_SIZE]:
					gif_aggregate.append(gif)

			gif_aggregate.sort(key=lambda gif: gif['timestamp'], reverse=True)

			gif_aggregate = gif_aggregate[:CHUNK_SIZE]

		else:
			# we need to build aggregate of gifs from people we are following
			gif_aggregate = []

			# we assume that user wants the latest feed content
			followers_cursor = mongo.db.follow.find({"follower": logged_in_user})
			for follow in followers_cursor:
				for gif in mongo.db.gif.find({"owner": follow['followed']}).sort("timestamp", -1)[:CHUNK_SIZE]:
					gif_aggregate.append(gif)

			gif_aggregate.sort(key=lambda gif: gif['timestamp'], reverse=True)

			gif_aggregate = gif_aggregate[:CHUNK_SIZE]

		feed = []

		# build up the dict for each gif
		for gif in gif_aggregate:
			gif_dict = {}
			gif_dict["username"] = mongo.db.user.find({"_id": ObjectId(gif["owner"])})[0]['username']
			gif_dict["user_id"] = gif["owner"]
			gif_dict["caption"] = gif["caption"]
			gif_dict["timestamp"] = gif["timestamp"]
			gif_dict["gif_url"] = "http://" + HOSTNAME + "/file/" + gif["name"] + ".gif"
			gif_dict["likes"] = __get_likes(gif["name"])
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