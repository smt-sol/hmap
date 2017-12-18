from iset import Box
from shapely.geometry import Polygon,Point

def outline(l,idx):
    T,B,L,R = (0,-1),(0,1),(-1,0),(1,0)
    noffs = [R,B]
    ncc = [L,B,R,T]
    nnext = {}

    for i in range(4):
        nnext[ncc[i]] = [ncc[(i-1)%4],ncc[i],ncc[(i+1)%4],ncc[(i+2)%4]]

    lab = l[idx]
    off = None

    for d in noffs:
        q = (idx[0]+d[0],idx[1]+d[1])
        if l[q] == lab:
            last = q
            off = (-d[0],-d[1])
            break
    else:
        return [idx,idx]

    x,y = idx
    pts = [last,(x,y)]
    x0,x1 = min(x,last[0]),max(x,last[0])
    y0,y1 = min(y,last[1]),max(y,last[1])

    while len(pts) == 2 or pts[1] != pts[-1] or pts[0] != pts[-2]:
        p = pts[-1]
        for d in nnext[off]:
            q = (p[0]+d[0],p[1]+d[1])
            if l[q] == lab:
                off = d
                last = p
                x0,x1 = min(x0,q[0]),max(x1,q[0])
                y0,y1 = min(y0,q[1]),max(y1,q[1])
                pts.append(q)
                break
        else:
            raise ValueError(p)
    return pts


def bnd2outer(data):
    def p4(p):
        return {
            "nw":(p[0],p[1]),
            "sw":(p[0],p[1]+1),
            "se":(p[0]+1,p[1]+1),
            "ne":(p[0]+1,p[1])
        }

    def add(ret,p):
        if len(ret) >= 2:
            q = ret[-1]
            r = ret[-2]
            if p[0] + r[0] == 2*q[0] and p[1] + r[1] == 2*q[1]:
                ret.pop()
            if ret[-1] == p:
                ret.pop()
        ret.append(p)

    p = tuple(data[0])
    q = p4(p)
    if len(data) == 2:
        assert p == tuple(data[1])
        return [q["nw"],q["sw"],q["se"],q["ne"],q["nw"]]

    assert tuple(data[0]) == tuple(data[-2])
    assert tuple(data[1]) == tuple(data[-1])

    ret = []
    n = len(data)
    for i in range(1,n-1):
        p0 = tuple(data[i-1])
        p1 = tuple(data[i])
        p2 = tuple(data[i+1])

        q = p4(p1)
        if p0 == p2: # go back
            if p1[0] > p0[0]: # R L
                add(ret,q["se"])
                add(ret,q["ne"])
                add(ret,q["nw"])
            elif p1[0] < p0[0]: # L R
                add(ret,q["nw"])
                add(ret,q["sw"])
                add(ret,q["se"])
            elif p1[1] > p0[1]: # D U
                add(ret,q["sw"])
                add(ret,q["se"])
                add(ret,q["ne"])
            elif p1[1] < p0[1]: # U D
                add(ret,q["ne"])
                add(ret,q["nw"])
                add(ret,q["sw"])
        elif p0[0]+p2[0] == 2*p1[0] and p0[1]+p2[1] == 2*p1[1]: #go straight
            pass
        elif p1[0] < p0[0] and p2[1] < p1[1]: # L U
            add(ret,q["ne"])
        elif p1[1] < p0[1] and p2[0] > p1[0]: # U R
            add(ret,q["se"])
        elif p1[0] > p0[0] and p2[1] > p1[1]: # R D
            add(ret,q["sw"])
        elif p1[1] > p0[1] and p2[0] < p1[0]: # D L
            add(ret,q["nw"])
        elif p1[0] < p0[0] and p2[1] > p1[1]: # L D
            add(ret,q["nw"])
            add(ret,q["sw"])
        elif p1[1] < p0[1] and p2[0] < p1[0]: # U L
            add(ret,q["ne"])
            add(ret,q["nw"])
        elif p1[0] > p0[0] and p2[1] < p1[1]: # R U
            add(ret,q["se"])
            add(ret,q["ne"])
        elif p1[1] > p0[1] and p2[0] > p1[0]: # D R
            add(ret,q["sw"])
            add(ret,q["se"])
        else:
            raise ValueError(p0,p1,p2)
    add(ret,ret[0])
    return ret

class Contour:
    def __init__(self,cnt,holes=None,att=None):
        self.cnt = cnt
        self.hls = holes if holes is not None else []
        self.att = att
        self.set_bb()
        self.shp = Polygon(reversed(cnt))

    def contains(self,other):
        if self.bb.contains(other.bb.x0,other.bb.y0) and \
           self.bb.contains(other.bb.x1,other.bb.y1):
            return self.contains_point(other.cnt[0])
        return False

    def contains_point(self,pt):
        return self.shp.contains(Point(pt))

    def add_hole(self,hole):
        self.hls.append(hole)

    @classmethod
    def from_idxlist(idxlist):
        return Contour()

    def set_bb(self):
        xs = {x[0] for x in self.cnt}
        ys = {x[1] for x in self.cnt}
        x0 = min(xs)
        x1 = max(xs)
        y0 = min(ys)
        y1 = max(ys)
        self.bb = Box(x0,y0,x1,y1)

    def shp_write(self,w,utm):
        llpoly = [list(reversed([(utm(*x)) for x in self.cnt]))]
        for cs in self.hls:
            utms = list(([(utm(*x)) for x in cs.cnt]))
            #latlon = [self.proj(*x,inverse=True) for x in utms]
            llpoly.append(utms) #latlon)
        if llpoly and llpoly[0]:
            #print("ATT",self.att,"LL",llpoly[:6])
            w.poly(llpoly)
            w.record(self.att)

    def pixels(self):
        return set(self.pout)

    def bbclose(self,other,dist):
        a,b,c,d = self.bbox
        e,f,g,h = other.bbox
        return not (a > f + dist or
                    e > b + dist or
                    c > h + dist or
                    g > d + dist)

    def gaps(self,other,gap):
        s = Data(self.pixels(),kdtree=True)
        o = Data(other.pixels(),kdtree=True)
        A = s.gaps(o,gap)
        holes = []
        for x in self.phls:
            holes += x
        if holes:
            s = Data(holes,kdtree=True)
            o = Data(other.pixels(),kdtree=True)
            A += s.gaps(o,gap)
        holes = []
        for x in other.phls:
            holes += x
        if holes:
            s = Data(self.pixels(),kdtree=True)
            o = Data(holes,kdtree=True)
            A += s.gaps(o,gap)
        return A


    def covers(self,p):
        return p in self.comp

a="""

def generate_contours(self):
        def area(v):
            return 0.5*sum(x[0]*y[1]-x[1]*y[0] for x,y in zip(v[:-1],v[1:]))

        def search(l,idx,lab):
            ret = {}
            idxs = [idx]
            seen = {idx}
            while idxs:
                i,j = idxs.pop()
                ilab = l[i,j]
                ret[ilab] = ret.get(ilab,0) + 1
                for idx in ((i,j-1),(i-1,j),(i+1,j),(i,j+1)):
                    if l[idx] != lab:
                        if idx not in seen:
                            idxs.append(idx)
                            seen.add(idx)
            return ret

        atts = sorted(self.show())
        a,l,s = self.hmap.wa_att,self.hmap.wa_lab,self.hmap.wa_siz
        x0,x1,y0,y1 = self.hmap.wa
        self.hmap.log(["generate contours"])
        self.hmap.statusBar().showMessage("generate contours A")

        PARA = self.hmap.parameters.get_all()
        CMIN = PARA["cmin"]
        HMIN = max(PARA["hmin"],CMIN)
        a2cset = {att:{} for att in atts}
        bpts = {att:set() for att in range(1,len(atts)+1)}

        for i in range(1,l.shape[0]-1):
            for j in range(1,l.shape[1]-1):
                lab = l[i,j]
                typ = a[i,j]

                if lab and (i,j) not in bpts[typ] and \
                   (l[i-1,j-1] != lab and l[i-1,j] == lab and l[i,j-1] == lab or\
                    l[i,j-1] != lab and l[i-1,j] != lab):
                    bnd = get_bnd(i,j,l)
                    att = atts[typ-1]
                    bpts[typ] |= set(bnd)
                    bnd = [(x+x0,y+y0) for (x,y) in bnd]
                    out = bnd2outer(bnd)
                    assert len(out) > 2
                    siz = area(out)
                    ok = (siz <= -CMIN or siz >= HMIN)
                    if siz > 0 and siz < HMIN:
                        if l[i,j-1] != lab:
                            idx = i,j-1
                        else:
                            idx = i-1,j-1
                        for k,v in search(l,idx,lab).items():
                            if k > 0 and v >= CMIN:
                                ok = False
                                break
                    if ok:
                        a2cset[att].setdefault(lab,[]).append((bnd,out,area(out)))

        self.hmap.statusBar().showMessage("generate contours B")
        for att in a2cset:
            self.a2cset[att] = {}
            self.a2poly[att] = {}
            for lab in a2cset[att]:
                C = Contour(sorted(a2cset[att][lab],key = lambda x:x[2]))
                self.a2cset[att][lab] = C
                self.a2poly[att][lab] = self.hmap.cnt2poly(C)


        self.hmap.statusBar().showMessage("generate contours C")
        self.cntUpdate.emit()
        self.changed.emit()


    def fix_contours(self):
        self.hmap.log(["fix contours"])
        self.hmap.statusBar().showMessage("FIX CONTOURS")
        PARA = self.hmap.parameters.get_all()
        GAP = PARA["gap"]
        PO = PARA["protect_overwrite"]

        for a in self.show():
            self.fix_contour(a,GAP,PO,greater=True)

        self.changed.emit()

    def clear_contours(self,att):
        if att in self.a2cset:
            del self.a2cset[att]
        if att in self.a2poly:
            for lab in self.a2poly[att]:
                for p in self.a2poly[att][lab]:
                    self.hmap.viewer.scene.removeItem(p)
            del self.a2poly[att]

    def fix_contour(self,att,gap,po,greater=False):
        self.hmap.statusBar().showMessage("FIX CONTOUR: " + att +\
                                          " GAP: " + str(gap))
        cset = list(self.a2cset[att].values())

        rest = {}
        scheme = self.hmap.selpara.get_color_scheme()
        pixs = self.all_pixs()

        for a in self.a2cset:
            if greater and a > att or not greater and a != att:
                rest[a] = list(self.a2cset[a].values())

        for i,x in enumerate(cset):
            self.hmap.statusBar().showMessage("Fix contour "+str(i)+" Att: "+att)
            xcol = self.a2o[att]
            xpar = xcol.getHsv()+xcol.getHsl()+xcol.getRgb()
            for ratt in rest:
                rcol = self.a2o[ratt]
                rpar = rcol.getHsv()+rcol.getHsl()+rcol.getRgb()
                for r in rest[ratt]:
                    if not x.bbclose(r,gap): continue
                    eqs = x.gaps(r,gap)
                    for (a,b) in eqs:
                        if not a: continue
                        d = Data(a|b)
                        c = d.convex_hull()
                        if po == "protect":
                            c -= pixs
                        if c:
                            del1 = set()
                            del2 = set()
                            for p in c:
                                col = self.hmap.selpara.image.pixelColor(*p)
                                if closer_color(col,xpar,rpar,scheme) == 0:
                                    del2.add(p)
                                else:
                                    del1.add(p)
                            self.a2pix[att].add(del2)
                            self.a2pix[ratt].add(del1)
        self.hmap.statusBar().showMessage("cleaning up")

        for a in self.a2pix:
            self.update_pixs(a)
        self.hmap.statusBar().showMessage("ATT:"+att+" READY")

    def remove_contours(self):
        self.hmap.log(["remove contours"])
        changed = False
        for a in self.show():
            self.clear_contours(a)
            changed = True
        if changed:
            self.changed.emit()

    def rsel_contours(self):
        if self.att in self.a2cset:
            self.clear_contours(self.att)
            self.changed.emit()

    def merge_contours(self):
        self.hmap.statusBar().showMessage("MERGE CONTOURS")
        PARA = self.hmap.parameters.get_all()
        GAP = PARA["gap"]
        PO = PARA["protect_overwrite"]

        for a in self.show():
            self.merge_contour(a,GAP,PO)

        self.changed.emit()

    def merge_contour(self,att,gap,po):
        self.hmap.log(["merge contours",att,str(gap)])
        self.hmap.statusBar().showMessage("MERGE CONTOUR: " + att + " GAP: " + str(gap))
        pixs = self.all_pixs()
        cset = self.a2cset.get(att,{})
        cnts = list(cset.values())
        a,l,s = self.hmap.wa_att,self.hmap.wa_lab,self.hmap.wa_siz
        x0,x1,y0,y1 = self.hmap.wa

        for i,x in enumerate(cnts):
            for y in cnts[i+1:]:
                if x.bbclose(y,gap):
                    eqs = x.gaps(y,gap)
                    for (a,b) in eqs:
                        if not a: continue
                        d = Data(a|b)
                        c = d.convex_hull()
                        if po == "protect":
                            c -= pixs
                        self.a2pix[att].add(c)

        self.update_pixs(att)
        #self.clear_contours(att)
        #self.add_contours(att)
        self.hmap.statusBar().showMessage("ATT:"+att+" READY")

    def add_contour(self,p):
        self.hmap.log(["att.add_contour",p])
        dmsg("WARNING","disabled")

    def sub_contour(self,p=None,lab=None):
        self.hmap.log(["att.sub_contour",p])
        if lab is None:
            assert p is not None
            i,j = p[0]-self.loff[0],p[1]-self.loff[2]
            lab = self.labels[1][i,j]
        for a in self.a2cset:
            if lab in self.a2cset[a]:
                rmatt = a
                break
        else:
            if lab is None:
                dmsg("WARNING","no contour found")
            return
        del self.a2cset[rmatt][lab]
        for p in self.a2poly[rmatt][lab]:
            self.hmap.viewer.scene.removeItem(p)
        del self.a2poly[rmatt][lab]
        self.changed.emit()
        self.cntUpdate.emit()
    def update_covers(self):
        atts = self.show()
        z = 1 if self.cntC.isChecked() else -1
        for a in self.a2poly:
            if a in atts:
                for lab in self.a2poly[a]:
                    for p in self.a2poly[a][lab]:
                        z = p.zValue()
                        if z < 0 and self.cntC.isChecked():
                            p.setZValue(z+1000000000)
                        if z > 0 and not self.cntC.isChecked():
                            p.setZValue(z-1000000000)
                        print("LAB Z",lab,p.zValue())
            else:
                for lab in self.a2poly[a]:
                    for p in self.a2poly[a][lab]:
                        z = p.zValue()
                        if z > 0:
                            p.setZValue(z-1000000000)
                        print("LAB Z",lab,p.zValue())




    def cnt2poly(self,cnt,checked=False):
        P = QPen(QColor(0,0,0))
        P.setWidth(0)
        B = QBrush(QColor(255,255,255,160),Qt.SolidPattern)
        B2 = QBrush(QColor(0,255,255,128),Qt.SolidPattern)

        polyF = QPolygonF([QPointF(x,y) for (x,y) in cnt.cout])
        poly = self.viewer.scene.addPolygon(polyF,P,B)
        poly.setZValue((1000000000 if checked else 0) - cnt.aout)

        holes = []
        for H,A in zip(cnt.chls,cnt.ahls):
            pF = QPolygonF([QPointF(x,y) for (x,y) in H])
            p = self.viewer.scene.addPolygon(pF,P,B2)
            p.setZValue((1000000000 if checked else 0) - A)
            holes.append(p)

        return [poly]+holes
"""
