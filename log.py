from functools import wraps

def sbar(f):
    @wraps(f)
    def new(self,*args,**d):
        self.log("sbar","start " + f.__module__ + ":" + f.__name__)
        ret = f(self,*args,**d)
        self.log("sbar")
        return ret
    return new

def logarg(f):
    @wraps(f)
    def new(self,*args,**d):
        self.log("edit",f.__name__ +" ARG: "+str([str(x) for x in args])+ " KARG: " + str({str(k):str(d[k]) for k in sorted(d.keys())}))
        print("edit",f.__name__ +" ARG: "+str([str(x) for x in args])+ " KARG: " + str({str(k):str(d[k]) for k in sorted(d.keys())}))
        ret = f(self,*args,**d)
        return ret
    return new

def logret(f):
    @wraps(f)
    def new(self,*args,**d):
        ret = f(self,*args,**d)
        self.log("edit",f.__name__ +" RET: "+str(ret))
        return ret
    return new



class Log:
    def __init__(self,sbar,mbox,warn,edit,dump):
        self.sbar = sbar
        self.mbox = mbox
        self.edit = edit
        self.warn = warn
        self.dump = dump

    def log(self,channel,msg=""):
        self.dump(msg)
        if channel == "sbar":
            if msg == "":
                msg = "READY"
            self.sbar(msg)
        elif channel == "popA":
            mbox = self.mbox
            cont = mbox(mbox.Information,"Yes/No",
                        msg,mbox.Yes|mbox.No).exec()
            return cont == mbox.Yes
        elif channel == "popE":
            mbox = self.mbox
            cont = mbox(mbox.Information,"ERROR",
                        msg,mbox.Ok).exec()
        elif channel == "popI":
            mbox = self.mbox
            cont = mbox(mbox.Information,"Information",
                        msg,mbox.Ok).exec()
        elif channel == "popW":
            mbox = self.mbox
            cont = mbox(mbox.Information,"Warning",
                        msg,mbox.Ok).exec()
        elif channel == "warn":
            self.warn(msg)
        elif channel == "edit":
            self.edit(msg)
        return None
