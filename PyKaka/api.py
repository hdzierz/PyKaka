import csv
import re
import pandas as pd
from pymongo import MongoClient
import pql
import yaml
import sys
import json 


MODE = "python2"
if sys.version_info >= (3, 0):
    print("Loading urllib for python 3")
    import urllib.request as urll
    import urllib.parse as parse
    MODE="python3"
elif sys.version_info > (2, 6) and sys.version_info  <  (3,0):
    print("Loading urllib for python >=2.7")
    import urllib
    import urllib2 as urll
else:
    raise Exception("PyKaka requires python > 2.6")


class Config:
    cfg = None
    def __init__(self, fn=None):
        if fn:
            s = open(fn, "r")
            self.cfg = yaml.load(s)
        else:
            self.cfg = {
                'mongo_host':'mongo',
                'mongo_port': 27017,
                'web_host': 'web',
                'web_port': 80,
            }

    def __getitem__(self,index):
        if index in self.cfg:
            return self.cfg[index]
        else:
            raise Exception("ERROR: " + str(index)  +  " not found in config.")

    def __setitem__(self,index,value):
        if index in self.cfg:
            self.cfg[index] = value
        else:
            raise Exception("ERROR: " + str(index)  +  " not found in config.")
            

cfg = Config()

def urlencode_qry(qry):
    print("Processing: " + qry)
    if sys.version_info >= (3, 0):
        return  parse.urlencode({"qry":qry, "infmt": "python"})
    elif sys.version_info > (2, 6) and sys.version_info  <  (3,0):
        return urllib.urlencode({"qry":qry, "infmt": "python"})
    else:
        raise Exception("PyKaka requires python > 2.6")


def check_config(cfg, send_mode):
    if not "DataSource" in cfg:
        print("Config needs a 'DataSource'")
        return False
    if not "Experiment" in cfg:
        print("Config needs 'Experiment' info")
        return False

    ds = cfg["DataSource"]
    if not "Format" in ds:
        print("Config DataSource needs a 'Format'.")
        return False
    if not "ID_Column" in ds and send_mode=="complete":
        print("The DataSource needs a unique 'ID_Column'.")
        return False
    if not "Name" in ds:
        print("The DataSource needs a unique 'Name'. Can be  file name or complete path.")
        return False
    if not "Creator" in ds and send_mode=="complete":
        print("DataSource does not know who has created it (Creator)")
        return False
    if not "Mode" in ds:
        print("DataSource does need a loading 'Mode' (Override, Clean, Append)")
        return False
    if not "Contact" in ds and send_mode=="complete":
        print("DataSource needs a 'Contact' email")
        return False

    ex = cfg["Experiment"]
    if not "Code" in ex:
        print("Experiment needs a unique name ('Code')")
        return False
    if not "Date" in ex and send_mode=="complete":
        print("Experiment needs a 'Date'")
        return False
    if not "Realm" in ex and send_mode=="complete":
        print("Experiment needs a 'Realm'")
        return False
    if not "Password" in ex:
        print("Please specify a 'Password' for your experiment. It will protect your data from being accidentally overriden by someone else.")
        return False
    if not "PI" in ex and send_mode=="complete":
        print("Experiment would like to know who the PI is")
        return False

    return True


class Kaka:
    @staticmethod
    def qry_mongo(realm, qry, cfg=Config()):
        host = cfg["mongo_host"]
        port = cfg["mongo_port"]

        client = MongoClient(host, port)
        db = client["primary"]
        try:
            coll = db[realm.lower()]
        except:
            raise Exception("realm not found")
        qry = pql.find(qry)
        res = coll.find(qry)
        dat = []
        for d in res:
            dat.append(d)
        print("Connecting to mongo://" + host + ":" + str(port))
        return pd.DataFrame(dat)

    @staticmethod
    def qry_pql(realm, expr, cfg=Config()):
        if(re.search("[a-zA-Z0-9\\s\'\"]=[a-zA-Z0-9\\s\'\"]",expr)):
            print("ERROR: You seem to have a single = in your expression. If it is a comparison operator use ==.")
            return None
       
        host = cfg["web_host"]
        port = cfg["web_port"]

        qry_str = urlencode_qry(expr)
        qry_str = "http://" + host + ":" + str(port) + "/qry/" + realm + "/?%s" % qry_str
        print(qry_str)
        return pd.read_csv(qry_str)

    @staticmethod
    def qry(realm, expr, mode="pql", columns = None, cfg=Config()):
        if(mode == "pql"):
            dat = Kaka.qry_pql(realm, expr, cfg=cfg)
        else:
            dat = Kaka.qry_mongo(realm, expr, cfg=cfg)

        if columns:
            return pd.DataFrame(dat, columns=columns)
        else:
            return dat

    @staticmethod
    def send_p2(data, config, host="web", port="80"):
        ser = json.dumps(data)
        config = json.dumps(config)
        opener = urll.build_opener(urll.HTTPHandler)
        request = urll.Request('http://' + host + ":" + port  +  '/send',
                          data='dat='+ser+"&config="+config+"&first", 
                          headers={'User-Agent' : "Magic Browser"})
        request.get_method = lambda: 'POST'
        url = opener.open(request)
        print(url.read()) 

    @staticmethod
    def send_p3(data, config, key, host="web", port="80"):
        ser = json.dumps(data)
        config = json.dumps(config)
        opener = urll.build_opener(urll.HTTPHandler)
       
        data = parse.urlencode({'dat':ser,"config":config})
        data = data.encode('ascii') 
        request = urll.Request('http://' + host + ":" + port  +  '/send',
                          data=data, 
                          headers={'User-Agent' : "Magic Browser"})
        request.get_method = lambda: 'POST'
        url = opener.open(request)
        print(url.read())


#    @staticmethod
#    def send_destroy(realm, experiment, data_source, key, cfg=cfg):
#        config = {"Experiment": {"Realm": realm, "Code": experiment, "Password": key}, "DataSource":{ "Name": data_source, "Format": "python_dict", "Mode": "Destroy"}}
#        data = {}
#        Kaka.send(data, config, cfg, "simple")
#
#    @staticmethod
#    def send_clean(experiment, key, cfg=cfg):
#         config = {"Experiment": {"Code": experiment}, "DataSource":{ "Name": data_source, "Mode": "Clean"}}
#         data = {}
#         Kaka.send(data, config, cfg, "simple")
#
#    @staticmethod
#    def send_override(data, experiment, data_source, key, cfg=cfg):
#        config = {"Experiment": {"Code": experiment}, "DataSource":{ "Name": data_source, "Mode": "Override"}}
#        Kaka.send(data, config, cfg, "simple")

    @staticmethod
    def send(data, config, cfg=cfg):
        if not check_config(config):
            return False

        host = cfg["web_host"]
        port = str(cfg["web_port"])

        if(hasattr(data, "to_dict")):
            data = data.to_dict(orient="records")
        if(MODE == "python3"):
            Kaka.send_p3(data, config, host, port)
        else:
            Kaka.send_p2(data, config, host, port)

