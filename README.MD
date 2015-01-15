## 10 Minute Chat in Python

A small example application using the `flowthings.io` platform

### Installation

This application was built using Python 2.x and Bottle.

Within the project directory:
```bash
virtualenv env
. env/bin/activate
cp settings-template.py settings.py
env/bin/pip install -r requirements.txt
env/bin/python 10minutechat.py
```
Browse to `localhost:8100` (or whatever you set your host / port to).

### Overview

The application demonstrates the following:

* A [Flow](https://flowthings.io/docs/flow-object-overview) to which we will send new chat messages
* A [Flow](https://flowthings.io/docs/flow-object-overview) from which we will receive chat messages
* A [Track](https://flowthings.io/docs/flow-object-overview) between the above Flows, which also contains the content-filtering logic
* A restricted [Token](https://flowthings.io/docs/flow-object-overview) object, which will be used for all participants of the chat room.

### Code Walkthrough

The main code is within these files:

* 10minutechat.py
* views/room.tpl

#### The Python Client

The demo uses the `flowthings.io` [Python Client](https://github.com/flowdotnet/flow-python-client-iot), the Bottle web framework, and JavaScript.

We begin by setting up the Python library:

```python
	user = ## your username
	master_token = ## your token

	creds = Token(user, master_token)
	api = API(creds, host="api.flowthings.io", secure=True)
```

We could put all of our chat rooms in our root Path, but to keep everything contained and organized we shall create a root path:

```python
	app_path = "/%s/10minutechat" % (user)
	api.flow.create({'path': app_path})
```

This Flow won't itself hold any data. You can think of it as creating a directory on a Unix filesystem.

#### Creating the Send / Receive Flows

Each time a user requests a new Chat Room, we'll first pick a new random path, and create the Flows we need under the path:

```python

	# Room Base Path
	random_path = ## create random string
    room_path = "%s/%s/" % (app_path, random_path
    api.flow.create({'path': room_path})

    # Create Flows
    send_flow_path = create_flow("%s/send" % room_path)
    receive_flow_path = create_flow("%s/receive" % room_path)

	api.flow.create({'path': send_flow_path, 'capacity': 0})
	api.flow.create({'path': receive_flow_path, 'capacity': 0})
```

 We have a choice here regarding the `capacity` of these Flows. A Flow's capacity determines how many Drops will be persisted on the platform before old Drops are deleted. A capacity of `0` will prevent any Drops from being persisted, but they will still move through the system like any other Drop.

#### Creating the Track and Filtering Logic

We need to create a Track between the `send` and `receive` Flows, and attach our content filtering JavaScript.

```python
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

    api.track.create({'source': send_flow_path, 'destination': receive_flow_path,
                             'js': js_func})
```
The JavaScript snippet is executed whenever a chat message is sent. For each chat message, we scan the content for a list of "forbidden" words. When we detect one, we replace the word with a randomly-selected "authorized" word, before returning it. This "sanitized" Drop is delivered to the `receive` Flow for everyone to view.

#### Creating the Limited-access Token

We can use a Token to grant limited access to the chatroom, with a 10 minute expiry. We can't have users consuming messages that haven't been sanitized of course, so we grant write-only access to the `send` Flow. We also don't want users bypassing the content-filter, so we grant read-only access to the `receive` Flow.

Finally, we set an expiry time of 10 minutes in the future.

```python
	millis = int(round(time.time() * 1000))
	token-object = api.token.create({
	        send_flow_path: {'dropRead': False, 'dropWrite':  True},
	        receive_flow_path: {'dropRead': True, 'dropWrite': False}},
	        expires_in_ms=millis + 600000)

```

The client returns an object representing a Token. This string is what the chat users will use to authenticate. This way, we've sandboxed our users. We generate a URL for people to use, which includes the new token string:

```python
	token-string = token-object["tokenString"]
	url = "http://%s:%s/room/join?room=%s" % (host, port, token_string)
```

#### WebSockets 

On the JavaScript side, after page-load we set up a Web Sockets connection, using the Token String previously generated. Once [authenticated](https://flowthings.io/docs/flowthings-websockets-api-authentication), we can subscribe to all messages from the Receive Flow:

```javascript
	request = $.ajax({
		        url: "https://{{ws_host}}/session",
		        beforeSend: function (req){
		    		req.setRequestHeader("X-Auth-Token", "{{token_string}}");
		    		req.setRequestHeader("X-Auth-Account", "{{flow_user}}");
		    		req.withCredentials = true
				},
		        type: "post",
		        dataType: 'json',
		        success: function(data){

		        	var sessionId = data["body"]["id"]
		        	var url = "ws://{{ws_host}}/session/" + sessionId + "/ws";

		        	connection = new WebSocket(url);

		        	connection.onopen = function () {
					  connection.send(subscribe());
					};
					connection.onerror = function (error) {
					  console.log('WebSocket Error ' + error);
					};
					connection.onmessage = function (e) {
					  var message = JSON.parse(e.data)
					  if (message.value){
					  	  console.log("Received: " + JSON.stringify(message.value))
						  var user = message.value.elems.user.value;
						  var content = message.value.elems.message.value;
						  addMessage(user,content)
					  }
					};
		        }
		    });

```

We can use the same connection to send chat messages:

```javascript
	$("#chatForm").submit(function(event){

	    var username = $("#username").val()
	    var content = $("#content").val()

	    if (content != ''){
	    	var message = dropMessage(username, content)
		    connection.send(message);
		    $("#content").val('')
	    }

	    event.preventDefault();
	});
```









