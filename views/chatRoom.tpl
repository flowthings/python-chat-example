<!DOCTYPE html>
<html>
<head>
	<title>10 Minute Flow Chat</title>
	<link rel="stylesheet" type="text/css" href="static/style.css" />
	<link href='http://fonts.googleapis.com/css?family=Source+Sans+Pro' rel='stylesheet' type='text/css'>
	<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>
	<script>
		var count={{timeLeft}};
		var connection;
 
		/**
			Hearbeat function
		*/
		function heartbeatWS(){
			connection.send(heartbeatMessage())
			console.log("WS Heartbeat")
		}

 		/**
			Create a countdown timer
 		*/
		function timer(){
		  count=count-1;
		  if (count <= 0){
		     window.location.replace("/finished");
		     return;
		  }

		  document.getElementById("timer").innerHTML="Time Left: " + count + " seconds"; // watch for spelling
		}

		/**
			Construct a Websocket message to subscribe to a Flow
		*/
		function subscribe() {
			return JSON.stringify({
			    "msgId": "chat-request",
			    "object": "drop",
			    "type": "subscribe",
			    "flowId": "{{receiveFlow}}"
			});
		}

		/**
			Construct a Websocket message to create a Drop
		*/
		function dropMessage(username, content){
			return JSON.stringify({
				"msgid" : "chat-msg", 
				"object" : "drop", 
				"type" : "create", 
				"flowId" : "{{sendFlow}}", 
				"value" : {
					"elems" : {
						"user" : username, 
						"message" : content
					}
				}
			});
		}

		function heartbeatMessage(){
			return JSON.stringify({
			  "type": "heartbeat"
			});
		}

		/**
			Add the received message to Chat window
		*/
		function addMessage(user,content){
			jQuery('<div/>', {
			    class: "chatline",
			    text: user + ": " + content
			}).appendTo('#chatbox');
			$("#chatbox").attr({ scrollTop: $("#chatBox").attr("scrollHeight") });
		}


		$(document).ready(function() {
			var request;

			/**
				Set up the send-message process
			*/
			$("#chatForm").submit(function(event){

			    var username = $("#username").val()
			    var content = $("#content").val()

			    if (content != ''){
			    	var message = dropMessage(username, content)
				    console.log("Sending: " + message)
				    connection.send(message);
				    $("#content").val('')
			    }

			    event.preventDefault();
			});

			/**
				Set up WebSockets
			*/
			request = $.ajax({
			        url: "https://{{wsHost}}/session",
			        beforeSend: function (req){
                		req.setRequestHeader("X-Auth-Token", "{{tokenString}}");
                		req.setRequestHeader("X-Auth-Account", "{{flowUser}}");
                		req.withCredentials = true
            		},
			        type: "post",
			        dataType: 'json',
			        success: function(data){

			        	var sessionId = data["body"]["id"]
			        	var url = "ws://{{wsHost}}/session/" + sessionId + "/ws";

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
			// Add a default message
			addMessage("System", "Welcome to 10-minute Flow Chat!")

			// Start the countdown
			var counter=setInterval(timer, 1000);
			var counter=setInterval(heartbeatWS, 10000);
		});
	</script>
</head>
<body>
<div style="text-align:center">
<div id="logo">
	<img id="flow" src="static/flow-logo.svg" />
	<span id="chat">things.... Chat!</span>
</div>
<h3 id="timer">Time Left: {{timeLeft}} seconds</h3>
<p><span class="bold">Banned words:</span> "XML", "Enterprise Java Beans"</p>
<div id="mainContent">
<div id="chatbox">
</div>
<form id="chatForm">
<label for="username">Your Name:</label>
<input type="text" id="username" name="username" class="chatinput">
<label for="content">Message:</label>
<input type="text" id="content" name="content" class="chatinput">
<input type="submit" value="Send it!" />
<input type="hidden" name="room" value="{{tokenString}}" />
<input type="hidden" name="destination" value="{{sendFlow}}" />
</form>
</div>
</div>
</body>
</html>