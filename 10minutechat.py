from bottle import route, run, request, response, template, view, post, static_file, redirect
from flow_things import API, Token, mem, MATCHES
from settings import SETTINGS
import random
import string
import time
import functools

##
# Settings
##
user = SETTINGS["user"]
master_token = SETTINGS["master_token"]
creds = Token(user, master_token)
api = API(creds, host="api.flowthings.io", secure=True)
app_path = "/%s/10minutechat" % (user)
host = SETTINGS["host"]
port = SETTINGS["port"]


##
# Create a Flow
##
def create_flow(path):
    return api.flow.create({'path': path, 'capacity': 0})

##
# Create the Track between Flows
##


def create_track(source, destination):

    js_func = """function (input){
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

    return api.track.create({'source': source, 'destination': destination,
                             'js': js_func})

##
# Create a Token
##


def create_token(receive_path, send_path):
    millis = int(round(time.time() * 1000))
    return api.token.create({
        send_path: {'dropRead': False, 'dropWrite':  True},
        receive_path: {'dropRead': True, 'dropWrite': False}},
        expires_in_ms=millis + 600000)

##
# Utility Functions
##


def create_api(token_string):
    return API(Token(user, token_string), host="api.flowthings.io", secure=False, ws_host="ws.flowthings.io")


def chat_link(token_string):
    return "http://%s:%s/room/join?room=%s" % (host, port, token_string)


def base_path_created():
    resp = api.flow.find(mem.path == app_path)
    print str(resp)
    return len(resp) > 0


def random_path():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9))


def create_application():
    if (base_path_created() == False):
        resp = api.flow.create({'path': app_path})

    return "Application ready to rock!"

##
# Routes
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


@route('/room/create')
@view('created')
def create():

    # Room Base Path
    room_path = "%s/%s/" % (app_path, random_path())
    api.flow.create({'path': room_path})

    # Create Flows
    send_flow = create_flow("%s/send" % room_path)
    receive_flow = create_flow("%s/receive" % room_path)

    print("Send Flow is: (%s , %s)" % (send_flow["id"], send_flow["path"]))
    print("Receive Flow is: (%s , %s)" %
          (receive_flow["id"], receive_flow["path"]))

    track = create_track(send_flow["path"], receive_flow["path"])

    print("Track is: (%s)" % (track["id"]))

    token = create_token(receive_flow["path"], send_flow["path"])

    print("Token is: (%s)" % (token["tokenString"]))

    return {"url":chat_link(token["tokenString"])}


@route('/setup')
def setup():
    return create_application()


@route('/room/join')
@view('room')
def chat():
    token_string = request.query.room

    # Create the restricted API
    chat_api = create_api(token_string)

    # Query send and receive
    try:
        receive_flow = chat_api.flow.find(mem.path.re('receive$', 'i'))[0]
        send_flow = chat_api.flow.find(mem.path.re('send$', 'i'))[0]
    except:
        redirect("/finished")

    # Query how long we have left
    token_object = chat_api.token.find()[0]
    expires = token_object['expiresInMs']
    now = int(round(time.time() * 1000))
    time_left = (expires - now) / 1000

    return {"token_string":token_string, "receive_flow":receive_flow["id"], "send_flow":send_flow["id"], 
            "time_left":time_left, "flow_user":user, "ws_host":"ws.flowthings.io"}


# Run the server
run(host=host, port=port, debug=True)
