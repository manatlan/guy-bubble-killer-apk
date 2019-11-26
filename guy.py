#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# #############################################################################
#    Apache2 2019 - manatlan manatlan[at]gmail(dot)com
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
#    more: https://github.com/manatlan/guy
# #############################################################################

#python3 -m pytest --cov-report html --cov=guy .


#TODO:
# cookiejar

__version__="0.3.9"

import os,sys,re,traceback,copy,types
from urllib.parse import urlparse
from threading import Thread
import tornado.web
import tornado.websocket
import tornado.platform.asyncio
import tornado.autoreload

import platform
import json
import asyncio
import time
import socket
from datetime import datetime,date
import tempfile
import subprocess
import webbrowser
import concurrent
import inspect
import uuid

class FULLSCREEN: pass
ISANDROID = "android" in sys.executable
LOG=None
FOLDERSTATIC="static"

GETPATH=os.getcwd
if hasattr(sys, "_MEIPASS"):  # when freezed with pyinstaller ;-)
    GETPATH=lambda: sys._MEIPASS

def isFree(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    return not (s.connect_ex((ip,port)) == 0)

#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#
https={}
def http(regex): # decorator
    if not regex.startswith("/"): raise Exception("http decoraton, path regex should start with '/'")
    def _(method):
        https["^"+regex[1:]+"$"] = method
    return _

async def callhttp(web,path): # web: RequestHandler
    for name,method in https.items():
        g=re.match(name,path)
        if g:
            if asyncio.iscoroutinefunction( method ):
                ret=await method(web,*g.groups())
            else:
                ret=method(web,*g.groups())
            if isinstance(ret,Guy):
                web.instance._children[ret._name]=ret
                web.render( ret )
            return True
#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#=#


def log(*a):
    if LOG:
        print(" ".join([str(i) for i in a]))

def serialize(obj):
    def toJSDate(d):
        assert type(d) in [datetime, date]
        d = datetime(d.year, d.month, d.day, 0, 0, 0, 0) if type(d) == date else d
        return d.isoformat() + "Z"

    if isinstance(obj, (datetime, date)):
        return toJSDate(obj)
    if isinstance(obj, bytes):
        return str(obj, "utf8")
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)


def unserialize(obj):
    if type(obj) == str:
        if re.search(r"^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z$", obj):
            return datetime.strptime(obj, "%Y-%m-%dT%H:%M:%S.%fZ")
        elif re.search(r"^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ$", obj):
            return datetime.strptime(obj, "%Y-%m-%dT%H:%M:%SZ")
    elif type(obj) == list:
        return [unserialize(i) for i in obj]
    return obj


def jDumps(obj):
    return json.dumps(obj, default=serialize)


def jLoads(s):
    return unserialize(
        json.loads(s, object_pairs_hook=lambda obj: {k: unserialize(v) for k, v in obj})
    )


class JDict:
    def __init__(self, f: str):
        self.__f = f
        try:
            with open(self.__f, "r+") as fid:
                self.__d = (
                    json.load(
                        fid,
                        object_pairs_hook=lambda obj: {
                            k: unserialize(v) for k, v in obj
                        },
                    )
                    or {}
                )
        except FileNotFoundError as e:
            self.__d = {}

    def set(self, k: str, v):
        self.__d[k] = v
        self.__save()

    def get(self, k: str = None):
        return self.__d.get(k, None) if k else self.__d

    def __save(self):
        with open(self.__f, "w+") as fid:
            json.dump(self.__d, fid, indent=4, sort_keys=True, default=serialize)

class GuyJSHandler(tornado.web.RequestHandler):
    def initialize(self, instance):
        self.instance=instance
    async def get(self,page=""):
        if page==self.instance._name or page=="":
            log("GuyJSHandler: Render Main guy.js",self.instance._name)
            self.write(self.instance._renderJs())
        else:
            chpage=self.instance._children.get(page,None)
            if chpage is not None:
                log("GuyJSHandler: Render Children guy.js",page)
                self.write(chpage._renderJs(asChild=True))
            else:
                raise tornado.web.HTTPError(status_code=404)

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, instance):
        self.instance=instance
    async def get(self,page): # page doesn't contains a dot '.'
        #####################################################
        if not await callhttp(self,page):
        #####################################################
            if page=="" or page==self.instance._name:
                log("MainHandler: Render Main Instance",self.instance._name)
                self.render(self.instance)
            else:
                chpage=self.instance._children.get(page,None)
                if chpage is None:
                    chpage=self.instanciate(page)
                if chpage:
                    log("MainHandler: Render Children",page)
                    self.render(chpage)
                else:
                    raise tornado.web.HTTPError(status_code=404)

    async def post(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)
    async def put(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)
    async def delete(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)
    async def options(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)
    async def head(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)
    async def patch(self,page): # page doesn't contains a dot '.'
        await self._callhttp(page)

    def instanciate(self,page,*a,**k):
        declared = {cls.__name__:cls for cls in Guy.__subclasses__()}
        gclass=declared.get(page,None)
        if gclass: # auto instanciate !
            log("MainHandler: Auto instanciate",page)
            self.instance._children[page]=gclass(*a,**k)
            return self.instance._children[page]

    def render(self,instance):
        """ write rendered instance """
        self.write(instance._render( GETPATH() ))

    async def _callhttp(self,page):
        if not await callhttp(self,page):
          raise tornado.web.HTTPError(status_code=404)



class ProxyHandler(tornado.web.RequestHandler):
    def initialize(self, instance):
        self.instance=instance
    async def get(self,**kwargs):
        await self._do("GET",None,kwargs)
    async def post(self,**kwargs):
        await self._do("POST",self.request.body,kwargs)
    async def put(self,**kwargs):
        await self._do("PUT",self.request.body,kwargs)
    async def delete(self,**kwargs):
        await self._do("DELETE",self.request.body,kwargs)

    async def _do(self,method,body,qargs):
        url = qargs.get('url')
        if self.request.query:
            url = url + "?" + self.request.query
        headers = {k[4:]: v for k, v in self.request.headers.items() if k.lower().startswith("set-")}

        http_client = tornado.httpclient.AsyncHTTPClient()
        log("PROXY FETCH",method,url,headers,body)
        try:
            response = await http_client.fetch(url, method=method,body=body,headers=headers,validate_cert = False)
            self.set_status(response.code)
            for k, v in response.headers.items():
                if k.lower() in ["content-type", "date", "expires", "cache-control"]:
                    self.set_header(k,v)
            log("PROXY FETCH",response.code,"size=",len(response.body))
            self.write(response.body)
        except Exception as e:
            log("PROXY FETCH ERROR",e,"return 0")
            self.set_status(0)
            self.write(str(e))


async def sockwrite(wsock, **kwargs ):
    if wsock:
        try:
            await wsock.write_message(jDumps(kwargs))
        except Exception as e:
            print("Socket write : can't")
            if wsock in WebSocketHandler.clients: del WebSocketHandler.clients[wsock]


async def emit(event,*args):
    log(">>> Emit ALL:",event,args)
    clients=list( WebSocketHandler.clients.keys() )
    for i in clients:
        await sockwrite(i,event=event,args=args)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    clients={}

    def initialize(self, instance):
        self.instance=instance

    def open(self):
        new=self.instance._initCopy( self )

        WebSocketHandler.clients[self]=new

    def on_close(self):
        del WebSocketHandler.clients[self]

    async def on_message(self, message):

        instance = WebSocketHandler.clients[self]

        o = jLoads(message)
        log("WS RECEPT:",o)
        method,args,uuid = o["command"],o["args"],o["uuid"]

        if method == "emit":
            event, *args = args
            await emit( event, *args )
        else:
            async def execution(function, uuid,mode):
                log("Execute (%s)"%mode,method,args)
                try:
                    ret = await function()
                    ##############################################################
                    if type(ret)==dict and "script" in ret: #evil mode
                        s=ret["script"]
                        del ret["script"]
                        r = dict(result=ret,script=s, uuid=uuid) #evil mode
                    else:
                    ##############################################################
                        r = dict(result=ret, uuid=uuid)
                except concurrent.futures._base.CancelledError as e:
                    r = dict(error="task cancelled", uuid=uuid)
                except Exception as e:
                    r = dict(error=str(e), uuid=uuid)
                    print("=" * 40, "in ", method, mode)
                    print(traceback.format_exc().strip())
                    print("=" * 40)
                log(">>> (%s)"%mode,r)
                await sockwrite(self,**r)

            fct=instance._getRoutage(method)

            if asyncio.iscoroutinefunction( fct ):

                async def function():
                    return await instance(method,*args)

                #asyncio.create_task( execution( function, uuid, "ASYNC") )  #py37
                asyncio.ensure_future ( execution( function, uuid, "ASYNC") ) #py35

            else:
                async def function():
                    return instance(method,*args)

                await execution( function, uuid, "SYNC" )

    def check_origin(self, origin):
        return True


class WebServer(Thread): # the webserver is ran on a separated thread
    port = 39000
    def __init__(self,instance,host="localhost",port=None):
        super(WebServer, self).__init__()
        self.instance=instance
        self.host=host

        if port is not None:
            self.port = port

        while not isFree("localhost", self.port):
            self.port += 1

        try: # https://bugs.python.org/issue37373 FIX: tornado/py3.8 on windows
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except:
            pass

    def run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        tornado.platform.asyncio.AsyncIOMainLoop().install()
        #~ tornado.autoreload.start()
        #~ tornado.autoreload.watch( sys.argv[0] )

        app=tornado.web.Application([
            (r'/ws',            WebSocketHandler,dict(instance=self.instance)),
            (r'/_/(?P<url>.+)', ProxyHandler,dict(instance=self.instance)),
            (r'/guy.js',        GuyJSHandler,dict(instance=self.instance)),
            (r'/(?P<page>[^/]+)/guy.js',        GuyJSHandler,dict(instance=self.instance)),
            (r'/(?P<page>[^\\.]*)',  MainHandler,dict(instance=self.instance)),
            (r'/(.*)',          tornado.web.StaticFileHandler, {'path': os.path.join( GETPATH(), FOLDERSTATIC) })
        ])
        app.listen(self.port,address=self.host)

        self.loop=asyncio.get_event_loop()

        async def _waitExit():
            while self._exit==False:
                await asyncio.sleep(0.1)

        self._exit=False
        self.loop.run_until_complete(_waitExit())

        # gracefull death
        ## tasks = asyncio.all_tasks(self.loop) #py37
        tasks = asyncio.Task.all_tasks(self.loop) #py35
        for task in tasks: task.cancel()
        try:
            self.loop.run_until_complete(asyncio.gather(*tasks))
        except concurrent.futures._base.CancelledError:
            pass

    def exit(self):
        self._exit=True

    @property
    def startPage(self):
        return "http://localhost:%s/#%s" % (self.port,self.instance._name) #anchor is important ! (to uniqify ressource in webbrowser)


class ChromeApp:
    def __init__(self, url, size=None, chromeArgs=[]):
        self.__instance = None

        def find_chrome_win():
            import winreg  # TODO: pip3 install winreg

            reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"
            for install_type in winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE:
                try:
                    with winreg.OpenKey(install_type, reg_path, 0, winreg.KEY_READ) as reg_key:
                        return winreg.QueryValue(reg_key, None)
                except WindowsError:
                    pass

        def find_chrome_mac():
            default_dir = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if os.path.exists(default_dir):
                return default_dir


        if sys.platform[:3] == "win":
            exe = find_chrome_win()
        elif sys.platform == "darwin":
            exe = find_chrome_mac()
        else:
            for i in ["chromium-browser", "chromium", "google-chrome", "chrome"]:
                try:
                    exe = webbrowser.get(i).name
                    break
                except webbrowser.Error:
                    exe = None

        if exe:
            args = [exe, "--app=" + url] + chromeArgs
            if size == FULLSCREEN:
                args.append("--start-fullscreen")
            if tempfile.gettempdir():
                args.append(
                    "--user-data-dir=%s"
                    % os.path.join(tempfile.gettempdir(), ".guyapp_"+re.sub(r"[^\w]","_",url))
                )
            log("CHROME APP-MODE:",args)
            self.__instance = subprocess.Popen(args)
        else:
            raise Exception("no chrome browser, no app-mode !")

    def wait(self):
        self.__instance.wait()

    def exit(self):
        self.__instance.kill()


class ChromeAppCef:
    def __init__(self, url, size=None, chromeArgs=None):  # chromeArgs is not used
        import pkgutil

        assert pkgutil.find_loader("cefpython3"), "cefpython3 not available"

        def cefbrowser():
            from cefpython3 import cefpython as cef
            import ctypes

            isWin = platform.system() == "Windows"

            windowInfo = cef.WindowInfo()
            windowInfo.windowName = "Guy-CefPython3"
            if type(size) == tuple:
                w, h = size[0], size[1]
                windowInfo.SetAsChild(0, [0, 0, w, h])  # not win
            else:
                w, h = None, None

            sys.excepthook = cef.ExceptHook

            settings = {
                "product_version": "Wuy/%s" % __version__,
                "user_agent": "Wuy/%s (%s)" % (__version__, platform.system()),
                "context_menu": dict(
                    enabled=True,
                    navigation=False,
                    print=False,
                    view_source=False,
                    external_browser=False,
                    devtools=True,
                ),
            }
            cef.Initialize(settings, {})
            b = cef.CreateBrowserSync(windowInfo, url=url)

            if isWin and w and h:
                window_handle = b.GetOuterWindowHandle()
                SWP_NOMOVE = 0x0002  # X,Y ignored with SWP_NOMOVE flag
                ctypes.windll.user32.SetWindowPos(
                    window_handle, 0, 0, 0, w, h, SWP_NOMOVE
                )

            # ===---
            def wuyInit(width, height):
                if size == FULLSCREEN:
                    if isWin:
                        b.ToggleFullscreen()  # win only
                    else:
                        b.SetBounds(0, 0, width, height)  # not win

            bindings = cef.JavascriptBindings()
            bindings.SetFunction("wuyInit", wuyInit)
            b.SetJavascriptBindings(bindings)

            b.ExecuteJavascript("wuyInit(window.screen.width,window.screen.height)")
            # ===---

            class WuyClientHandler(object):
                def OnLoadEnd(self, browser, **_):
                    pass  # could serve in the future (?)

            class WuyDisplayHandler(object):
                def OnTitleChange(self, browser, title):
                    try:
                        cef.WindowUtils.SetTitle(browser, title)
                    except AttributeError:
                        print(
                            "**WARNING** : title changed '%s' not work on linux" % title
                        )

            b.SetClientHandler(WuyClientHandler())
            b.SetClientHandler(WuyDisplayHandler())
            log("CEFPYTHON :",url)
            return cef

        self.__instance=cefbrowser()

    def wait(self):
        self.__instance.MessageLoop()

    def exit(self):
        self.__instance.Shutdown()



class Guy:
    _wsock=None     # when cloned and connected to a client/wsock (only the cloned instance set this)
    _runned=None    # (only the main instance set this)
    _children={}

    size=None
    def __init__(self,*a,**k):
        self._name = self.__class__.__name__
        self._id=self._name+"-"+uuid.uuid4().hex
        self.callbackExit=None      #public callback when "exit"

        self._routes={}
        for n, v in inspect.getmembers(self, inspect.ismethod):
            if not v.__func__.__qualname__.startswith("Guy."):
                if n not in ["init","__init__"]:
                    if n!="_render":
                        if n in dir(Guy): raise Exception("Can't set route '%s' (existing keyword))"%n)
                    self._routes[n]=v

        # guy's inner routes
        self._routes["cfg_get"]=self.cfg_get
        self._routes["cfg_set"]=self.cfg_set
        self._routes["exit"]=self.exit


    def _initCopy(self,wsock):
        log("CLONE",self._name)
        keys=self._routes.keys()
        self._routes={}
        new = copy.copy(self)
        for n, v in inspect.getmembers(new):
            if n in keys:
                if inspect.isfunction(v):
                    new._routes[n]=types.MethodType( v, new ) #rebound !
                else:
                    new._routes[n]=v

        new._wsock = wsock
        self._runned = new

        try:
          if hasattr(new,"init"):
              new.init(new)
        except TypeError:
          pass

        return new


    def run(self,log=False):
        """ Run the guy's app in a windowed env (one client)"""
        global LOG
        LOG=log
        if ISANDROID: #TODO: add executable for kivy/iOs mac/apple
            runAndroid(self)
        else:
            os.chdir( os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0]))) )

            ws=WebServer( self )
            ws.start()

            app=ChromeApp(ws.startPage,self.size)

            def exit():
                ws.exit()
                app.exit()

            self.callbackExit = exit
            try:
                app.wait() # block
            except KeyboardInterrupt:
                print("-Process stopped")

            ws.exit()
            ws.join()

        return self._runned

    def runCef(self,log=False):
        """ Run the guy's app in a windowed cefpython3 (one client)"""
        global LOG
        LOG=log

        os.chdir( os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0]))) )
        ws=WebServer( self )
        ws.start()

        app=ChromeAppCef(ws.startPage,self.size)
        self.callbackExit = app.exit
        try:
            app.wait() # block
        except KeyboardInterrupt:
            print("-Process stopped")
        ws.exit()
        ws.join()
        return self._runned


    def serve(self,port=8000,log=False,open=True):
        """ Run the guy's app for multiple clients (web/server mode) """
        global LOG
        LOG=log

        os.chdir( os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0]))) )
        ws=WebServer( self ,"0.0.0.0",port=port )
        ws.start()

        def exit():
            ws.exit()

        self.callbackExit = exit
        print("Running", ws.startPage )

        if open: #auto open browser
            try:
                import webbrowser
                webbrowser.open_new_tab(ws.startPage)
            except:
                pass

        try:
            ws.join() #important !
        except KeyboardInterrupt:
            print("-Process stopped")
        ws.exit()
        return self._runned #TODO: technically multiple cloned instances can have be runned (which one is the state ?)

    def exit(self):
        if self.callbackExit: self.callbackExit()

    def cfg_set(self, key, value): setattr(self.cfg,key,value)
    def cfg_get(self, key=None):   return getattr(self.cfg,key)

    @property
    def cfg(self):
        class Proxy:
            def __init__(self):
                if ISANDROID:
                    self.__o=JDict(os.path.join( os.getcwd(),"..","config.json"))
                else:
                    self.__o=JDict(os.path.join( os.getcwd(),"config.json"))
            def __setattr__(self,k,v):
                if k.startswith("_"):
                    super(Proxy, self).__setattr__(k, v)
                else:
                    self.__o.set(k,v)
            def __getattr__(self,k):
                if k.startswith("_"):
                    return super(Proxy, self).__getattr__(k)
                else:
                    return self.__o.get(k)
        return Proxy()


    def _renderJs(self,asChild=False):
        if self.size and self.size is not FULLSCREEN:
            size=self.size
        else:
            size=None
        routes=[k for k,v in self._routes.items() if not v.__func__.__qualname__.startswith("Guy.")]
        log("ROUTES:",routes)
        js = """
document.addEventListener("DOMContentLoaded", function(event) {
    %s
    %s
},true)



function setupWS( cbCnx ) {
    var url=window.location.origin.replace("http","ws")+"/ws"
    var ws=new WebSocket( url );

    ws.onmessage = function(evt) {
      var r = guy._jsonParse(evt.data);
      guy.log("** WS RECEPT:",r)
      if(r.uuid) // that's a response from call py !
          document.dispatchEvent( new CustomEvent('guy-'+r.uuid,{ detail: r} ) );
      else if(r.event){ // that's an event from anywhere !
          document.dispatchEvent( new CustomEvent(r.event,{ detail: r.args } ) );
      }
    };

    ws.onclose = function(evt) {
        guy.log("** WS Disconnected");
        setTimeout( function() {setupWS(cbCnx)}, 500);
    };
    ws.onerror = function(evt) {
        guy.log("** WS Disconnected");
        setTimeout( function() {setupWS(cbCnx)}, 500);
    };
    ws.onopen=function(evt) {
        guy.log("** WS Connected")
        cbCnx(ws);
    }

    return ws;
}

var guy={
    _jsonParse: function(x) {
        function reviver(key, value) {
            const dateFormat = /^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$/;
            if (typeof value === "string" && dateFormat.test(value))
                return new Date(value);
            else
                return value;
        }
        return JSON.parse(x, reviver )
    },
    _log: %s,
    log:function(_) {
        if(guy._log) {
            var args=Array.prototype.slice.call(arguments)
            args.unshift("--")

            console.log.apply(console.log,args.map( function(x) {return x==null?"NULL":x}));
        }
    },
    _ws: setupWS( function(ws){guy._ws = ws; document.dispatchEvent( new CustomEvent("init") )} ),
    on: function( evt, callback ) {     // to register an event on a callback
        guy.log("guy.on:","DECLARE",evt,callback.name)
        var listener=function(e) { callback.apply(callback,e.detail) };
        document.addEventListener(evt,listener)
        return function() { document.removeEventListener(evt, listener) }
    },

    emitMe: function( _) {        // to emit to itself
        let ll=Array.prototype.slice.call(arguments)
        let evt=ll.shift()
        guy.log("guy.emitMe:", evt,ll)
        document.dispatchEvent( new CustomEvent(evt,{ detail: ll }) );
    },

    emit: function( _ ) {        // to emit a event to all clients
        var args=Array.prototype.slice.call(arguments)
        guy.log("guy.emit:", args)
        return guy._call("emit", args)
    },
    init: function( callback ) {
        function start() {
            guy.log("guy.init:",callback.name)
            document.removeEventListener("init", start)
            callback()
        }
        if(guy._ws.readyState == guy._ws.OPEN)
            start()
        else
            document.addEventListener("init", start)
    },
    _call: function( method, args ) {
        guy.log("guy.call:","CALL",method,args)
        var cmd={
            command:    method,
            args:       args,
            uuid:       method+"-"+Math.random().toString(36).substring(2), // stamp the exchange, so the callback can be called back (thru customevent),
        };

        if(guy._ws) {
            guy._ws.send( JSON.stringify(cmd) );

            return new Promise( function (resolve, reject) {
                document.addEventListener('guy-'+cmd.uuid, function handler(x) {
                    guy.log("guy.call:","RESPONSE",method,"-->",x.detail)
                    this.removeEventListener('guy-'+cmd.uuid, handler);
                    var x=x.detail;
                    if(x && x.result!==undefined) {
                        if(x.script)
                            resolve( eval(x.script) )
                        else
                            resolve(x.result)
                    }
                    else if(x && x.error!==undefined)
                        reject(x.error)
                });
            })
        }
        else
            return new Promise( function (resolve, reject) {
                reject("not connected");
            })
    },
    fetch: function(url,obj) {
        guy.log("guy.fetch:", url, "body:",obj)

        var h={"cache-control": "no-cache"};    // !!!
        if(obj && obj.headers)
            Object.keys(obj.headers).forEach( function(k) {
                h["set-"+k]=obj.headers[k];
            })
        var newObj = Object.assign({}, obj)
        newObj.headers=h;
        newObj.credentials= 'same-origin';
        return fetch( "/_/"+url,newObj )
    },
    cfg: new Proxy({}, {
      get: function (obj, prop) {
        return guy._call("cfg_get",[prop])
      },
      set: function (obj, prop, value) {
        return guy._call("cfg_set",[prop,value]);
      },
    }),
    exit: function() {guy._call("exit",[])},

    _instanciateWindow: async function(o) {
        guy.log("Window "+o.name+":","Instanciate, routes=",o.routes);

        self={
            parent: self,
            _promise: new Promise( function (resolve, reject) {
                guy.on(o.event, function(r) {
                    guy.log("Window "+o.name+":","Exited, return = ",r)
                    self._div.parentNode.removeChild(self._div);
                    self=self.parent;
                    resolve( guy._jsonParse(r) )
                })
            }),
            _div: (function(html){
                var tag_div=document.createElement("div");
                tag_div.innerHTML = html
                document.body.appendChild(tag_div);
                return tag_div;
            })(o.html),
            exit: function() {guy.emitMe(o.event, null)},
            run: function() {
                guy.log("Window "+o.name+":","Running")
                return self._promise;
            },
        }

        for(var key of o.routes) {
            (function _(key,id) {
                self[key]=function(_) {return guy._call(id+"."+key, Array.prototype.slice.call(arguments) )}
            })(key,o.id);
        }

        var tag_js=document.createElement("script");
        tag_js.setAttribute('type', 'text/javascript');
        tag_js.innerHTML = o.scripts
        self._div.appendChild(tag_js)

        return self;
    },

};


var self= {
  exit:function() {guy.exit()},
  %s
};



""" % (
        size and "window.resizeTo(%s,%s);" % (size[0], size[1]) or "",
        'if(!document.title) document.title="%s";' % self._name,
        "true" if LOG else "false",
        "\n".join(["""\n%s:function(_) {return guy._call("%s", Array.prototype.slice.call(arguments) )},""" % (k, asChild and self._id+"."+k or k) for k in routes])
    )

        return js

    async def emit(self, event, *args):
        await emit(event, *args)

    async def emitMe(self,event, *args):
        log(">>> emitMe",event,args)
        await sockwrite(self._wsock,event=event,args=args)

    def _getRoutage(self,method):
        function=None
        if "." in method:
            id,method = method.split(".")
            for i in self._children.values():
                if i._id == id:
                    log("METHOD CHILD",i._name,method)
                    function=i._routes[method]
        else:
            log("METHOD SELF",method)
            function=self._routes[method]
        return function

    def __call__(self,method,*args):

        function = self._getRoutage(method)

        ret= function(*args)

        if isinstance(ret,Guy):
            ################################################################
            self._children[ ret._name ]=ret
            o=ret

            routes=[k for k in o._routes.keys() if not k.startswith("_")]

            eventExit="event-"+o._id+".exit"
            def exit():
                log("USE %s: EXIT" % o._name,o._json)
                # asyncio.create_task(self.emitMe(eventExit,o._json)) #  py37
                asyncio.ensure_future(self.emitMe(eventExit,o._json)) # py35


            html=o._render(GETPATH(),includeGuyJs=False)
            scripts=";".join(re.findall('(?si)<script>(.*?)</script>', html))

            o.callbackExit=exit
            if hasattr(o,"init"): o.init(o)
            obj=dict(
                id=o._id,
                name=o._name,
                html=html,
                routes=routes,
                event=eventExit,
                scripts=scripts,

                script="guy._instanciateWindow(x.result)"
            )
            return obj
            ################################################################

        return ret

    def _render(self,path,includeGuyJs=True):
        html=self.__doc__

        def rep(x):
            d=self.__dict__
            d.update(self.__class__.__dict__)
            for rep in re.findall("<<[^><]+>>", x):
                var = rep[2:-2]
                if var in d:
                    o=d[var]
                    if type(o)==str:
                        x=x.replace(rep, o)
                    else:
                        x=x.replace(rep, jDumps( o ))
            return x

        def repgjs(x,page):
          return re.sub('''src *= *(?P<quote>["'])[^(?P=quote)]*guy\\.js[^(?P=quote)]*(?P=quote)''','src="/%s/guy.js"'%page,x)

        if html:
            if includeGuyJs: html=("""<script src="guy.js"></script>""")+ html
            html=repgjs(html,self._name)
            return rep(html)
        else:
            f=os.path.join(path,FOLDERSTATIC,"%s.html" % self._name)
            if os.path.isfile(f):
                with open(f,"r") as fid:
                    b=fid.read()
                    b=repgjs(b,self._name)
                    return rep(b)
            else:
                return "ERROR: can't find '%s'" % f

    @property
    def _dict(self):
        obj={k:v for k,v in self.__dict__.items() if not (k.startswith("_") or callable(v))}
        for i in ["callbackExit","__doc__","_children","size"]:
            if i in obj: del obj[i]
        return obj

    @property
    def _json(self):
        """ return a json representation of the inner attributs of this"""
        return jDumps(self._dict)


def runAndroid(ga):
    import kivy
    from kivy.app import App
    from kivy.utils import platform
    from kivy.uix.widget import Widget
    from kivy.clock import Clock
    from kivy.logger import Logger

    def run_on_ui_thread(arg):
        pass

    webView       = None
    webViewClient = None
    #~ webChromeClient = None
    activity      = None
    if platform == 'android':
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
        webView       = autoclass('android.webkit.WebView')
        webViewClient = autoclass('android.webkit.WebViewClient')
        #~ webChromeClient = autoclass('android.webkit.WebChromeClient')
        activity      = autoclass('org.kivy.android.PythonActivity').mActivity



    class Wv(Widget):
        def __init__(self, guyWindow ):
            self.f2 = self.create_webview # important
            super(Wv, self).__init__()
            self.visible = False

            def exit():
                activity.finish()
                App.get_running_app().stop()
                os._exit(0)

            guyWindow.callbackExit = exit

            self.ws=WebServer( guyWindow )
            self.ws.start()

            Clock.schedule_once(self.create_webview, 0)

        @run_on_ui_thread
        def create_webview(self, *args):
            webview = webView(activity)
            webview.getSettings().setJavaScriptEnabled(True)
            webview.getSettings().setDomStorageEnabled(True)
            webview.setWebViewClient(webViewClient())
            #~ webview.setWebChromeClient(webChromeClient())
            activity.setContentView(webview)
            webview.loadUrl(self.ws.startPage)

    class ServiceApp(App):
        def build(self):
            return Wv( ga )

    ServiceApp().run()



if __name__ == "__main__":
    #~ from testTordu import Tordu as GuyApp
    # from testPrompt import Win as GuyApp
    # GuyApp().run()
    pass

