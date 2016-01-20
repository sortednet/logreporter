# -*- coding: utf-8 -*-
__doc__ = """
A simple chat example using a CherryPy webserver.

$ pip install cherrypy

Then run it as follow:

$ python app.py

You will want to edit this file to change the
ws_addr variable used by the websocket object to connect
to your endpoint. Probably using the actual IP
address of your machine.
"""
from Queue import Queue
import threading
import subprocess
import random
import os
import re
import cherrypy

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

# filename and regex should be args
filename = "log.log"
regex = ".*T[0-9]*\w.*"

cur_dir = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
index_path = os.path.join(cur_dir, 'index.html')
index_page = file(index_path, 'r').read()

queue = Queue()

class ChatWebSocketHandler(WebSocket):
    def received_message(self, m):
        cherrypy.engine.publish('websocket-broadcast', m)

    def closed(self, code, reason="A client left the room without a proper explanation."):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

class ChatWebApp(object):
    @cherrypy.expose
    def index(self):
        return index_page % { 'ws_addr': 'ws://localhost:9000/ws'}

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

def publishLogs():
    while True:
        message = queue.get(True);
        cherrypy.engine.publish('websocket-broadcast', message) 
        print "Published message: ", message


def addLog(logLine):
   message = logLine.rstrip()
   queue.put(message)
   print "added message: ", message


def tailFile():
    f = subprocess.Popen(['tail','-F',filename],\
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    while True:
        line = f.stdout.readline()
        if (line):
            addLog(line)



matcher = re.compile(regex)
tailThread = threading.Thread(target=tailFile)
tailThread.start()
pubThread = threading.Thread(target=publishLogs)
pubThread.start()

cherrypy.config.update({
    'server.socket_host': '0.0.0.0',
    'server.socket_port': 9000
})
    
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

cherrypy.quickstart(ChatWebApp(), '',
                    config={
                        '/': {
                            'tools.response_headers.on': True,
                            'tools.response_headers.headers': [
                                ('X-Frame-options', 'deny'),
                                ('X-XSS-Protection', '1; mode=block'),
                                ('X-Content-Type-Options', 'nosniff')
                            ]
                        },
                        '/ws': {
                            'tools.websocket.on': True,
                            'tools.websocket.handler_cls': ChatWebSocketHandler
                        },
                    })

print "Now to tail the file"
tailFile()

