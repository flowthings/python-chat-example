from bottle import route, run, request, response, template, view, post, static_file, redirect
from flow_things import API, Token, mem, MATCHES
from settings import SETTINGS
import random
import string
import time
import functools

##
## Settings
##
user = SETTINGS["user"]
masterToken = SETTINGS["masterToken"]
creds = Token(user, masterToken)
api = API(creds, host="api.flowthings.io", secure=True)
appPath = "/%s/10minutechat" % (user)
host = SETTINGS["host"]
port = SETTINGS["port"]


##
## Create a Flow
##
def createFlow(path):
	return api.flow.create({'path' : path, 'capacity' : 0})

## 
## Create the Track between Flows
##
def createTrack(source, destination):

	jsFunc = """function (input){
	    var acceptableWords = ['Loosely-Coupled Architecture', 'JSON'];

	    var text = input.elems.message.value;
	    var forbiddenWords = new RegExp('Enterprise Java Beans|XML','ig');

	    function randomAcceptableWord(){
		    var index = Math.floor(Math.random()*(acceptableWords.length)+0);
		    return acceptableWords[index];
	    }

	    text = text.replace(forbiddenWords, randomAcceptableWord());

	    input.elems.message.value = text
	    return input;
	  }"""

	return api.track.create({'source' : source, 'destination' : destination,
		'js' : jsFunc})

##
## Create a Token
##
def createToken(receivePath, sendPath):
	millis = int(round(time.time() * 1000))
	return api.token.create({
		sendPath : {'dropRead' : False, 'dropWrite' :  True},
		receivePath : {'dropRead' : True, 'dropWrite' : False}},
		expires_in_ms=millis+600000)

##
## Utility Functions
##
def createApi(tokenString):
	return API(Token(user, tokenString), host="api.flowthings.io", secure=False, ws_host="ws.flowthings.io")

def chatLink(tokenString):
	return "http://%s:%s/chat?room=%s" % (host, port, tokenString)

def basePathCreated():
	resp = api.flow.find(mem.path==appPath)
	print str(resp)
	return len(resp) > 0

def randomPath():
	return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9))

def createApplication():
	if (basePathCreated() == False):
		resp = api.flow.create({'path' : appPath})

	return "Application ready to rock!"

##
## Routes
##
@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root='static/')

@route('/')
@view('index')
def index():
	return {}

@route('/finished')
@view('finished')
def finished():
	return {}

@route('/createRoom')
@view('roomCreated')
def create():
	
	## Room Base Path
	roomPath = "%s/%s/" % (appPath, randomPath())
	api.flow.create({'path' : roomPath})

	## Create Flows
	sendFlow = createFlow("%s/send" % roomPath)
	receiveFlow = createFlow("%s/receive" % roomPath)
	
	print ("Send Flow is: (%s , %s)" % (sendFlow["id"], sendFlow["path"]))
	print ("Receive Flow is: (%s , %s)" % (receiveFlow["id"], receiveFlow["path"]))

	track = createTrack(sendFlow["path"], receiveFlow["path"])
	
	print ("Track is: (%s)" % (track["id"]))
	
	token = createToken(receiveFlow["path"], sendFlow["path"])

	print ("Token is: (%s)" % (token["tokenString"]))

	return dict(url=chatLink(token["tokenString"]))

@route('/setup')
def setup():
	return createApplication()

@route('/chat')
@view('chatRoom')
def chat():
	tokenString = request.query.room

	## Create the restricted API
	chatApi = createApi(tokenString)

	## Query send and receive
	try:
		receiveFlow = chatApi.flow.find(mem.path.re('receive$', 'i'))[0]
		sendFlow = chatApi.flow.find(mem.path.re('send$', 'i'))[0]
	except:
		redirect("/finished")

	## Query how long we have left
	tokenObject = chatApi.token.find()[0]
	expires = tokenObject['expiresInMs']
	now = int(round(time.time() * 1000))
	timeLeft = (expires - now) / 1000


	return dict(tokenString=tokenString, receiveFlow=receiveFlow["id"], sendFlow=sendFlow["id"], timeLeft=timeLeft,
		flowUser=user, wsHost="ws.flowthings.io")


## Run the server
run(host=host, port=port, debug=True)