import sys
import os
from flask import Flask
from flask import request
import base64
import datetime
import psycopg2 as pg
import traceback
from datetime import datetime as dt
from bs4 import BeautifulSoup as bs

def format_exception(e)-> str:
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
    exception_str = "Traceback (most recent call last):\n"
    exception_str += "".join(exception_list)
    # Removing the last \n
    exception_str = exception_str[:-1]

    return exception_str

class Config:
    def __init__(self):
        self.db_host = os.environ['POSTGRES_HOST']
        if not self.db_host:
            self.db_host = "localhost"
        self.db_port = int(os.environ['POSTGRES_PORT'])
        if not self.db_port:
            self.db_port = 5432
        self.db_user = os.environ['POSTGRES_USER']
        self.db_pass = os.environ['POSTGRES_PASSWORD']
        self.db_name = os.environ['POSTGRES_DB']
        if not self.db_user or not self.db_pass or not self.db_name:
            raise Exception("invalid env. check your .env file and recreate container")

class LogEntry:
    def __init__(self):
        self.e = ""
        self.raw = ""
        self.msg = ""
        self.app = ""
        self.node = ""
        self.level = 9

class HtmlTemplates:
    def __init__(self):
        self.invalidreqHtml = '''
        <html>
        <body>
        <div style='
            color: black;
            background: red;
            padding: 16px;
            font-size: 24px;
            font-family: monospace;
            border-radius: 8px;
        '> invalid request </div>
        </body>
        </html>'''
        self.header = '''
            <html>
            <head>
            <title>%s</title>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            <style>
            body {
                padding: 0;
                margin: 0;
                background: #253536;
            }
            pre {
                border-radius: 0.25rem;
                background-color: #fafafa;
                padding: 1.5rem 1rem;
                box-shadow: 0 2px 18px 0 rgb(0 0 0 / 14%%);
            }
            .container {
                border-radius: 0.25rem;
                background-color: #fafafa;
                padding: 1.5rem 1rem;
                box-shadow: 0 2px 18px 0 rgb(0 0 0 / 14%%);
                margin: 3px;
            }
            .btn {
                color: #fff;
                background-color: #5bb75b;
                background-image: -moz-linear-gradient(top,#62c462,#51a351);
                background-image: -webkit-gradient(linear,0 0,0 100%%,from(#62c462),to(#51a351));
                background-image: -webkit-linear-gradient(top,#62c462,#51a351);
                background-image: -o-linear-gradient(top,#62c462,#51a351);
                background-image: linear-gradient(to bottom,#62c462,#51a351);
                border-color: rgba(0,0,0,.1) rgba(0,0,0,.1) rgba(0,0,0,.25) rgba(0,0,0,.1);
                background-repeat: repeat-x;
                text-shadow: 0 -1px 0 rgb(0 0 0 / 25%%);
                vertical-align: middle;
                cursor: pointer;
                display: inline-block;
                padding: 4px 12px;
                margin-bottom: 0;
                font-size: 14px;
            }
            .btn:focus, .btn:hover {
                color: #333;
                text-decoration: none;
                transition: color  .2s linear;
            }
            .row {
                text-decoration: none; 
                background-color: #fafafa;
                font-family: monospace;
                font-size: 12px;
            }
            .row:hover {
                font-weight: bold;
                background-color: #ffe9e9;
            }
            
            </style>
            <script>
            function doClean() {
                $.ajax({
                    url: "/clean"
                    }).done(function(data) {
                        alert("clean - " + data)
                        location.reload(true)
                    });
            }
            </script>
            </head>
            <body>
            '''
        self.footer = '''
        </body>
        </html>
        '''


class LogServer:
    def __init__(self):
        self.cfg = Config()
        self.insertQuery = "INSERT INTO public.simplelog(i, level, app, node, message) VALUES (%s, %s, %s, %s, %s);"
        self.okresponce = "ok\n\n"
        self.errorResponce = "fail\n\n"
        self.dataTable = "simplelog"
        self.maxiKey = "maxi"
        self.conn = None
        self.cur = None
        self.i = 0
        self.tpl = HtmlTemplates()
    def connect(self)-> bool:
        self.disconnect()
        print("connect to %s:%d::%s" %( self.cfg.db_host, self.cfg.db_port, self.cfg.db_name ))
        self.conn = pg.connect(user = self.cfg.db_user ,
                                password = self.cfg.db_pass,
                                host = self.cfg.db_host,
                                port = self.cfg.db_port,
                                database = self.cfg.db_name)
        if not self.conn:
            self.disconnect()
            return False
        self.cur = self.conn.cursor()
        return True

    def disconnect(self):
        if self.cur:
            self.cur.close()
            self.cur = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def offsetLimit(self)->int:
        if not self.cur:
            self.serverLog("not connected to db")
            return 0
        self.cur.execute("SELECT value_i FROM public.samplelogproperties WHERE key = '%s'" % self.maxiKey)
        record = self.cur.fetchone()
        if not record:
            return 0
        return int(record[0])
        
    def maxi(self)->int:
        if not self.cur:
            self.serverLog("not connected to db")
            return 0
        self.cur.execute("SELECT MAX(i) as maxi FROM public.simplelog WHERE message is not null;")
        record = self.cur.fetchone()
        if not record:
            return 0
        return int(record[0])


    def insert(self, entry):
        if not self.cur:
            self.serverLog("not connected to db")
            return
        #d = (int(entry.level), entry.app.strip(), entry.node.strip(), urlsafe_b64encode(entry.msg.strip().encode('utf8')))
        self.i += 1
        self.cur.execute(self.insertQuery,
                                (str(self.i + int(dt.now().timestamp() * 10000)), 
                                str(int(entry.level)),
                                entry.app.strip(), 
                                entry.node.strip(),
                                entry.msg.strip()))
        self.conn.commit()

    def serverLog(self, msg):
        print((str(datetime.datetime.now())+ " server said: " + msg), flush = True)
      
        
    def processBrowse(self, request) ->str:
        page = self.tpl.header % "logserver"
        page += "<div><input type = 'button' class='btn' onclick = 'doClean()' value = 'Clean'>  </div>"
        page += "<div class= 'container'>"
        q = "SELECT dt, app, node, message FROM public.simplelog WHERE message is not null AND i > %d ORDER BY i ASC " % self.offsetLimit()
        self.cur.execute(q)
        for row in self.cur.fetchall():
            page += "<div class='row'>%s %s:%s - %s</div>\n" % (row[0], row[1], row[2], base64.urlsafe_b64decode(row[3].encode('utf8')).decode('utf8'))
        page += "</div>"
        page += self.tpl.footer
        return page

    def processClean(self, request) ->str:
        i = self.maxi()
        if i <= 0:
            return "nothing to do"
        try:
            self.cur.execute("UPDATE public.samplelogproperties set value_i = %d where key = 'maxi';" % i)
        except Exception as e:
            return "NIET! " + str(e)
        return "DA! " + str(i)


    def processAdd(self, request) ->str:
        self.serverLog(str(request.data))
        if request.method != 'POST':
            return self.tpl.invalidreqHtml
        j = request.get_json()
        entry = LogEntry()
        entry.e = j.get('e')
        entry.raw = j.get('msg')
        entry.msg = entry.raw
        entry.app = j.get('app')
        entry.node = j.get('node')
        entry.level = int(j.get('level'))
        validMsg = False
        try:
            if base64.urlsafe_b64decode(entry.raw):
                validMsg = True
        except: 
            validMsg = False
        if not validMsg:
            return "invalid message encoding"
        entry.msg= entry.raw
        try:
            self.insert(entry)
            return self.okresponce
        except Exception as e:
            self.print("cannot save record: reason " + format_exception(e))
        return self.errorResponce

app = Flask(__name__)
server = LogServer()

@app.route('/add', methods = ['GET', 'POST'])
def addMessage():
    return server.processAdd(request)

@app.route('/clean')
def cleanList():
    return server.processClean(request)

@app.route('/', methods = ['GET', 'POST'])
def browse():
    txt = server.processBrowse(request)
    soup = bs(txt, "html.parser")
    return soup.prettify()


if __name__ == '__main__':
    rc = server.connect()
    if not rc:
        print("cannot connect")
        exit(1)
    app.run("0.0.0.0", 1514)