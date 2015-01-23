<!DOCTYPE html>
<html>
<head>
	<title>10 Minute Flow Chat</title>
	<link rel="stylesheet" type="text/css" href="static/style.css" />
	<link href='http://fonts.googleapis.com/css?family=Source+Sans+Pro' rel='stylesheet' type='text/css'>
</head>
<body>
<div style="text-align:center">
<div id="logo">
	<img id="flow" src="static/flow-logo.svg" />
	<span id="chat">things.... Chat!</span>
</div>

<div id="mainContent">

%if valid_settings == False:
<div id="warning">
	Your username and / or Master Token settings are invalid! Please double check your settings.py file!
</div>
%end
	<p>Visit <a href="http://flowthings.io">flowthings.io</a> for more info</p>	

	Welcome to 10-minute Flowthings Chat. This demonstration uses the following Flowthings platform objects:

	<ul>
		<li>A <a href="https://flowthings.io/docs/flow-object-overview">Flow</a> to which we will send new chat messages</li>
		<li>A <a href="https://flowthings.io/docs/flow-object-overview">Flow</a> from which we will receive chat messages</li>
		<li>A <a href="https://flowthings.io/docs/track-object-overview">Track</a> between the above Flows, which also contains the content-filtering logic</li>
		<li>A restricted <a href="https://flowthings.io/docs/token-object-overview">Token</a> object, which will be used for all participants of the chat room</li>
	</ul> 

</div>
<form action="/room/create" method="GET">
	<input type="submit" value="Create new chat room"/>
</form>

</div>
</body>
</html>