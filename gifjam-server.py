import os
from flask import Flask, request, make_response
from werkzeug.utils import secure_filename
from moviepy.editor import *
from flask.ext.pymongo import PyMongo, ObjectId
from uuid import uuid4
from gridfs import GridFS
import time

UPLOAD_FOLDER = 'file-uploads'
ALLOWED_EXTENSIONS = set(['mp4'])
DEBUG = True

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo = PyMongo(app)

def allowed_file(filename):
	"""Takes in a filename and returns whether or not it is of the allowed filetype."""
	return '.' in filename and \
		filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route("/")
def hello():
	return "Hello Tribe Hacks!"

@app.route("/init")
def db_init():
	"""Crappy helper function that inits some db values."""
	mongo.db.user.insert({"name":"root"})
	return ""

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
		print cursor[0]["_id"]
		return cursor[0]["_id"]

def __insertGifInDb(name, caption, owner_oid):
	"""Inserts the gif into the db"""
	mongo.db.gif.insert({"name": name, "caption":caption, "owner":owner_oid, "timestamp":int(time.time())})

@app.route("/profilefeed")
def profile_feed():
	"""Takes in a lastDate and user GET variables. Returns the next food in the feed"""
	params = request.args
	if 'user' in params:
		user = params['user']
		if 'lastDate' in params:
			# a last date was specified.
			# sort the elements in the cursor by timestamp
			mongo.db.gif.sort("")
			# get the top 5 elements after lastDate
			# for each of these top 5 elements:
				# make them a json dict
			return params['lastDate']
		else:
			# assume that we want the most recent
			cursor = mongo.db.gif.find({"name": user})
			# sort the elements in the cursor by timestamp
			# get the top 5 elements
			# for each of these top 5 elements:
				# make them a json dict

			return user
	else:
		return "A user needs to be specified"

if __name__ == "__main__":
	if DEBUG:
		app.run(host="0.0.0.0", debug=True)
	else:
		app.run(host="0.0.0.0")