(function(root, factory) {
  var isNode = typeof require === 'function' && typeof exports === 'object';
  var XHR = function() {
    var test;
    try {
      test = new XMLHttpRequest();
    } catch(e) {
      test = {};
    }
    return test.withCredentials != null ? XMLHttpRequest
         : typeof XDomainRequest != 'undefined' ? XDomainRequest
         : isNode ? require('xmlhttprequest').XMLHttpRequest
         : null;
  }();
  var WS = function() {
    return typeof WebSocket !== 'undefined' ? WebSocket
         : isNode ? require('ws')
         : null;
  }();

  function init(exports) {
    return factory(exports, WS, XHR);
  }

  if (typeof define === 'function' && define.amd) {
    define(['exports'], init);
  } else if (isNode) {
    init(exports);
  } else {
    init(root.flow = {});
  }
}(this, function(flow, WS, XHR){

  flow.options = {
    secure: true,
    host: 'ws.flow.net',
    httpTimeout: 20000,
    heartbeatTimeout: 20000,
  };

  flow.connect = function(params, callback) {
    if (XHR == null) throw new Error('Not supported');
    if (typeof params === 'function') {
      callback = params;
      params = null;
    }
    handshake(params, function(err, sid) {
      if (err) throw new Error('Handshake failed');
      flow.attach(sid, callback);
    });
  };

  flow.attach = function(sid, callback) {
    if (XHR == null) throw new Error('Not supported');
    var client = WS ? FlowWebSocket(sid) : FlowXHR(sid);
    client.onopen = function() {
      if (callback) callback.call(this, client);
    };
    return client;
  };

  function proxy(method, context) {
    return function() {
      if (typeof context[method] === 'function') {
        context[method].apply(context, arguments);
      } else if (context[method] != null) {
        throw new TypeError('Expected function for callback: ' + method);
      }
    };
  }

  function Messages(client) {
    var replyId = 1;
    var replies = {};
    return {
      out: function(type, value, callback) {
        var envelope = { type: type, value: value };
        if (callback) {
          envelope.id = replyId++;
          replies[envelope.id] = callback;
        }
        return envelope;
      },
      in: function(envelope) {
        if (envelope.type === "reply" && envelope.id) {
          replies[envelope.id].call(client, envelope.value);
          delete replies[envelope.id];
        }
        return envelope;
      }
    }
  }

  function FlowWebSocket(sid) {
    var sessionUrl = (flow.options.secure ? 'wss' : 'ws') + '://' +
                      flow.options.host + '/session/' + sid + '/ws';
    var ws = new WS(sessionUrl);
    var client = {}
    var msgs = Messages(client);
    var closed = false;
    var hbTimer;

    client.subscribe = mkMethod('subscribe');
    client.unsubscribe = mkMethod('unsubscribe');
    client.close = function() {
      ws.close()
      closed = true;
    };

    ws.onopen = function() {
      runHeartbeat();
      proxy('onopen', client)();
    }
    ws.onclose = function() {
      closed = true;
      replies = ws = null;
      window.clearTimeout(hbTimer);
      proxy('onclose', client)();
    };
    ws.onmessage = function(e) {
      var message = msgs.in(JSON.parse(e.data));
      if (message.type === 'message') {
        proxy('onmessage', client)(message.value, message.resource);
      }
    };

    return client;

    // ---

    function runHeartbeat() {
      if (!closed) {
        hbTimer = window.setTimeout(function() {
          ws.send(JSON.stringify({ type: 'heartbeat' }));
          runHeartbeat();
        }, heartbeatTimeout());
      }
    }

    function mkMethod(type) {
      return function(value, callback) {
        if (closed) return;
        ws.send(JSON.stringify(msgs.out(type, value, callback)));
      }
    }
  }

  function FlowXHR(sid) {
    var sessionUrl = mkUrl('/session/' + sid + '/polling');
    var client = {};
    var msgs = Messages(client);
    var closed = false;
    var sendQueue = [];
    var sendTimer;
    var sendReq;
    var recvReq;
    var recvTimer;
    var pollTimer;

    client.subscribe = mkMethod('subscribe');
    client.unsubscribe = mkMethod('unsubscribe');
    client.close = function() {
      if (recvReq) recvReq.abort();
      if (sendReq) sendReq.abort();
      if (recvTimer) clearTimeout(recvTimer);
      if (sendTimer) clearTimeout(sendTimer);
      if (pollTimer) clearTimeout(pollTimer);
      sendQueue = recvReq = sendReq = recvTimer = sendTimer = pollTimer = null;
      closed = true;
      proxy('onclose', client)();
    };

    setTimeout(function() {
      receive();
      proxy('onopen', client)(client);
    }, 1);

    return client;

    // ---

    function send(message) {
      sendQueue.push(message);
      if (!sendTimer) sendTimer = setTimeout(flush, 1);
    }

    function receive() {
      recvReq = new XHR();
      recvReq.open('GET', sessionUrl + '?_=' + (new Date().getTime()), true);
      recvReq.onload = function() {
        clearTimeout(pollTimer);
        dispatch(JSON.parse(recvReq.responseText));
        recvTimer = setTimeout(receive, 1);
      };
      recvReq.onerror = client.close;
      recvReq.send();
      pollTimer = setTimeout(function() {
        recvReq.abort();
        recvTimer = setTimeout(receive, 1);
      }, httpTimeout());
    }

    function flush() {
      var top = sendQueue.shift();
      sendReq = new XHR();
      sendReq.open('POST', sessionUrl + '?_=' + (new Date().getTime()), true);
      sendReq.onload = function() {
        if (sendQueue.length) sendTimer = setTimeout(flush, 1);
        else sendTimer = null;
      };
      sendReq.onerror = client.close;
      sendReq.send(JSON.stringify(top));
    }

    function dispatch(messages) {
      var callback = proxy('onmessage', client);
      for (var i = 0; i < messages.length; i++) {
        var message = msgs.in(messages[i]);
        if (message.type === 'message') {
          callback(message.value, message.resource);
        }
      }
    }

    function mkMethod(type) {
      return function(value, callback) {
        if (closed) return;
        send(msgs.out(type, value, callback));
      }
    }
  }

  function httpTimeout() {
    return Math.max(flow.options.httpTimeout, 10000);
  }

  function heartbeatTimeout() {
    return Math.max(flow.options.heartbeatTimeout, 10000);
  }

  function handshake(params, callback) {
    var url = flow.options.handshakeProxy || mkUrl('/session');
    var xhr = new XHR();
    
    xhr.open('POST', url, true);
    for (var k in params) {
      if (params.hasOwnProperty(k)) {
        xhr.setRequestHeader(k,params[k].toString())
      }
    }
    xhr.onload = function() {
      callback(null, JSON.parse(xhr.responseText).body.id);
    };
    xhr.onerror = function() {
      callback(xhr, null);
    };
    xhr.send();
  }

  function mkUrl(path, params) {
    var url = (flow.options.secure ? 'https' : 'http') + '://' + flow.options.host + path;
    var qs = [];
    if (params) {
      for (var k in params) {
        if (params.hasOwnProperty(k)) {
          qs.push(k + '=' + encodeURIComponent(params[k].toString()));
        }
      }
    }
    return qs.length ? url + '?' + qs.join('&') : url;
  }
}));