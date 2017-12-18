from math import floor,ceil
import numpy as np
from scipy.spatial import ConvexHull,Delaunay,KDTree
from scipy.spatial.distance import euclidean
from scipy.cluster.vq import kmeans2
from skimage.measure import label

from datetime import datetime as dt

def make_box(mins,maxs,gaps=None):
    n = len(mins)
    assert n == len(maxs)
    if gaps is None:
        gaps = n * [1]
    lattice = {}
    for i in range(n):
        xmin = mins[i]
        xmax = maxs[i]
        m = (xmax-xmin) // gaps[i]
        lattice[i] = [xmin + j * gaps[i] for j in range(m+1)]
    pts = {()}
    for i in range(n):
        pts = {x + (y,) for x in pts for y in lattice[i]}
    return pts

def get_bnd(x,y,labels):
    noffs = [(0,-1),(1,0),(0,1)]
    ncc = [(-1,0),(0,1),(1,0),(0,-1)]
    nnext = {}
    for i in range(4):
        nnext[ncc[i]] = [ncc[(i-1)%4],ncc[i],ncc[(i+1)%4],ncc[(i+2)%4]]
    t = labels[x,y]
    for d in noffs:
        q = (x+d[0],y+d[1])
        if labels[q] == t:
            last = q
            off = (-d[0],-d[1])
            break
    else:
        dat = [(x,y),(x,y)]
        return dat#,True #,(x,x,y,y)

    pts = [last,(x,y)]
    x0,x1 = min(x,last[0]),max(x,last[0])
    y0,y1 = min(y,last[1]),max(y,last[1])

    while len(pts) == 2 or pts[1] != pts[-1] or pts[0] != pts[-2]:
        p = pts[-1]
        for d in nnext[off]:
            q = (p[0]+d[0],p[1]+d[1])
            if labels.get(q,-1) == t:
                off = d
                last = p
                x0,x1 = min(x0,q[0]),max(x1,q[0])
                y0,y1 = min(y0,q[1]),max(y1,q[1])
                pts.append(q)
                break
        else:
            raise ValueError(p)
    return pts
#if y0 == y1 or x0 == x1:
#        ccw = True
#   else:
#       a = [x for x in pts if x[0] == x0]
#        b = min(x[1] for x in a)
#        idx = pts.index((x0,b))
#        jdx = idx+1
#        step = 1
#        while pts[jdx][1] == b:
#            step = pts[jdx][0] - pts[idx][0]
#            jdx = (jdx + 1) % (len(pts)-2)
#
#        c = pts[jdx]
#        ccw = c[1] > b and step == 1 or c[1] < b and step == -1
#    return pts,ccw
#    #return pts #,(x0,x1,y0,y1)


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
        # print("P012",p0,p1,p2,end=" ")
        q = p4(p1)
        if p0 == p2: # go back
            if p1[0] > p0[0]: # R L
                # print("RL")
                add(ret,q["se"])
                add(ret,q["ne"])
                add(ret,q["nw"])
            elif p1[0] < p0[0]: # L R
                # print("LR")
                add(ret,q["nw"])
                add(ret,q["sw"])
                add(ret,q["se"])
            elif p1[1] > p0[1]: # D U
                # print("DU")
                add(ret,q["sw"])
                add(ret,q["se"])
                add(ret,q["ne"])
            elif p1[1] < p0[1]: # U D
                # print("UD")
                add(ret,q["ne"])
                add(ret,q["nw"])
                add(ret,q["sw"])
        elif p0[0]+p2[0] == 2*p1[0] and p0[1]+p2[1] == 2*p1[1]: #go straight
            # print("**")
            pass
        elif p1[0] < p0[0] and p2[1] < p1[1]: # L U
            # print("LU")
            add(ret,q["ne"])
        elif p1[1] < p0[1] and p2[0] > p1[0]: # U R
            # print("UR")
            add(ret,q["se"])
        elif p1[0] > p0[0] and p2[1] > p1[1]: # R D
            # print("RD")
            add(ret,q["sw"])
        elif p1[1] > p0[1] and p2[0] < p1[0]: # D L
            # print("DL")
            add(ret,q["nw"])
        elif p1[0] < p0[0] and p2[1] > p1[1]: # L D
            # print("LD")
            add(ret,q["nw"])
            add(ret,q["sw"])
        elif p1[1] < p0[1] and p2[0] < p1[0]: # U L
            # print("UL")
            add(ret,q["ne"])
            add(ret,q["nw"])
        elif p1[0] > p0[0] and p2[1] < p1[1]: # R U
            # print("RU")
            add(ret,q["se"])
            add(ret,q["ne"])
        elif p1[1] > p0[1] and p2[0] > p1[0]: # D R
            # print("DR")
            add(ret,q["sw"])
            add(ret,q["se"])
        else:
            raise ValueError(p0,p1,p2)
    add(ret,ret[0])
    return ret

class Data:
    """list of tuples"""
    def __init__(self,data,kdtree=False):
        if len(data) == 0:
            self.empty = True
            return
        self.empty = False
        self.data = np.array(list(data))
        self.sdat = {tuple(x) for x in self.data}
        self.shape = self.data.shape
        assert len(self.shape) == 2 # shape[0] = no. of tuples shape[1] = dimensions

        self.maxs = np.array([max(self.data[:,i]) for i in range(self.shape[1])])
        self.mins = np.array([min(self.data[:,i]) for i in range(self.shape[1])])
        self.kdtree = KDTree(self.data) if kdtree else None
        self.bbox = self.bb()

    def bb(self):
        ret = []
        for i in range(len(self.mins)):
            ret.append(self.mins[i])
            ret.append(self.maxs[i])
        return ret

    def ccw(self):
        s = 0
        for i in range(len(self.data)-1):
            p = self.data[i]
            q = self.data[i+1]
            s += p[0]*q[1]-p[1]*q[0]
        return s <= 0

    def bbclose(self,other,dist):
        a,b,c,d = self.bbox
        e,f,g,h = other.bbox

        return not (a > f + dist or
                    e > b + dist or
                    c > h + dist or
                    g > d + dist)

    def get_box(self,mins,maxs):
        if self.empty:
            return set()
        mins = np.maximum(mins,self.mins)
        maxs = np.minimum(maxs,self.maxs)
        dels = np.array([y-x for (x,y) in zip(mins,maxs)])
        center = mins + dels/2
        dmin = min(dels)
        dmax = max(dels)

        if dmin < 0:
            return set()

        if dmax > 3 * dmin:
            r = dmax/2 + 0.25
            pts = [center]
        else:
            r = dmin/2 + 0.25
            lattice = {}
            for i in range(self.shape[1]):
                xmin = mins[i]
                xmax = maxs[i]
                n = int(ceil(xmax-xmin)/(dmin/2))
                lattice[i] = [xmin + j * dmin/2 for j in range(1,n)]
            pts = [(x,) for x in lattice[0]]
            for i in range(1,self.shape[1]):
                pts = [x + (y,) for x in pts for y in lattice[i]]
        if self.kdtree is None:
            self.kdtree = KDTree(self.data)
        idxs = self.kdtree.query_ball_point(pts,r,np.inf)
        ret = {tuple(self.data[i])
               for y in idxs for i in y
               if np.all(self.data[i] >= mins) and np.all(self.data[i] <= maxs)}
        return ret & self.sdat

    def noff(self,diag=False,null=False,off=None):
        if self.empty:
            return set()
        xs = {()}
        off = range(-1,2) if off is None else off
        for i in range(self.shape[1]):
            xs = {x+(r,) for x in xs for r in off}
        if diag:
            if null:
                ret = xs
            else:
                ret = {x for x in xs if len([y for y in x if y != 0]) >= 1}
        else:
            if null:
                ret = {x for x in xs if len([y for y in x if y != 0]) <= 1}
            else:
                ret = {x for x in xs if len([y for y in x if y != 0]) == 1}
        return ret

    def component(self,pt,diag=False):
        if self.empty:
            return set()
        if self.shape[1] == 2:
            if diag:
                return self.component2D(pt,2)
            else:
                return self.component2D(pt,1)
        idxs = [np.array(pt)]
        pt = tuple(pt)
        if pt not in self.sdat:
            return set()
        found = {pt}
        noff = self.noff(diag)
        while idxs:
            pt = idxs.pop(0)
            for x in noff:
                e = pt + x
                t = tuple(e)
                if t not in found and t in self.sdat:
                    idxs.append(e)
                    found.add(t)
        return found

    def filled_component(self,pt,c1=None,diag=False):
        if self.empty:
            return set()
        c1 = Data(self.component(pt,diag)) if c1 is None else Data(c1)
        if c1.empty:
            return set()
        box = make_box(c1.mins-1,c1.maxs+2)
        c2 = Data(box - c1.sdat)
        s = c2.component(c1.mins-1)
        return box-s

    def convex_hull(self,onediff=True,restrict=None):
        if self.empty:
            return set()
        sdat = self.sdat
        noff = [np.array(x) for x in self.noff(diag=True,null=True)]

        if onediff:
            pts = [tuple(np.array(x) + n) for x in sdat for n in noff]
        else:
            pts = list(sdat)

        try:
            hull = Delaunay(pts)
        except:
            print("WARNING: COULD NOT CONSTRUCT HULL: " + str(len(pts)))
            return set(pts)

        d = Data(pts)
        box = make_box(d.mins,d.maxs)

        ret = set(pts)
        if restrict is not None:
            box &= restrict
            ret &= restrict

        for p in box:
            if hull.find_simplex(p) >= 0:
                ret.add(p)
        return ret

    def cluster(self,n=None,size=None):
        if self.empty:
            return {}
        if len(self.sdat) == 1:
            return {0:set(self.sdat)}
        try:
            if n is not None:
                centroids,labels = kmeans2(np.array(self.data,np.float),n)
                #K = KMeans(n_clusters = n)
                #newdata = K.fit_transform(self.data)
            else:
                assert size is not None
                n = 2
                while True:
                    #K = KMeans(n_clusters = n)
                    #newdata = K.fit_transform(self.data)
                    centroids,labels = kmeans2(np.array(self.data,np.float),n)
                    val = max((euclidean(self.data[i],centroids[labels[i]]) for i in range(len(self.data))))
                    if val <= size:
                        break
                    n += 1

            clusters = {i:set() for i in range(n)}
            for i,x in enumerate(self.data):
                clusters[labels[i]].add(tuple(x))
            return clusters
        except:
            return {0:set(self.sdat)}

    def dist(self,n,diag=True):
        if self.empty:
            return set()
        noff = self.noff(diag,null=True,off=range(-n,n+1))
        new = set()
        for pt in self.data:
            x = np.array(pt)
            for d in noff:
                new.add(tuple(x + d))
        return new

    def gaps(self,other,r):
        if self.empty or other.empty:
            return []
        if self.kdtree is None:
            self.kdtree = KDTree(self.data)
        if other.kdtree is None:
            other.kdtree = KDTree(other.data)

        a = self.kdtree.query_ball_tree(other.kdtree,r)
        b = other.kdtree.query_ball_tree(self.kdtree,r)
        c = {}
        d = {}
        for i,x in enumerate(a):
            if x:
                c[i] = set(x)
        for i,x in enumerate(b):
            if x:
                d[i] = set(x)
        eqs = []
        for a,b in galois_closure(c,d):
            aa = {tuple(self.data[i]) for i in a}
            bb = {tuple(other.data[i]) for i in b}
            eqs.append((aa,bb))
        return eqs

def galois_closure(c,d):
    eqs = set()
    cs = set()
    ds = set()
    for i in c:
        last = 0,0
        if i not in cs:
            a,b = {i},set(c[i])
            while (len(a),len(b)) != last:
                last = len(a),len(b)
                for x in b:
                    a |= set(d[x])
                for y in a:
                    b |= set(c[y])
            eqs.add((tuple(a),tuple(b)))
            cs |= a
            ds |= b
    for i,(a,b) in enumerate(eqs):
        print(i,sorted(a)[:8],sorted(b)[:8])
    return eqs

def genpix(s):
    a = [(0,0)]
    assert s.count("u") == s.count("d")
    assert s.count("r") == s.count("l")
    for c in s:
        p = list(a[-1])
        if c == "u": p[1] -= 1
        if c == "d": p[1] += 1
        if c == "l": p[0] -= 1
        if c == "r": p[0] += 1
        a.append(tuple(p))
    a.append(a[1])
    return a

#for s in ("drlu","durl","rdul"):
#    print(s)
#    a = genpix(s);print(a);b = Data(a); r=b.bnd2outer()
#    print(r)
#    print(40*"-")

class CData(Data):
    """'lists' of pixel indexes used to compute contours"""
    doffs = [(1,-1),(1,0),(1,1),(0,1),(-1,1)]
    noffs = [(1,0),(0,1)]
    dnext = {}
    dcc = [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
    for i in range(8):
        dnext[dcc[i]] = [dcc[(i-3)%8],dcc[(i-2)%8],dcc[(i-1)%8],dcc[i],
                         dcc[(i+1)%8],dcc[(i+2)%8],dcc[(i+3)%8],dcc[(i+4)%8]]

    nnext = {}
    ncc = [(-1,0),(0,1),(1,0),(0,-1)]
    for i in range(4):
        nnext[ncc[i]] = [ncc[(i-1)%4],ncc[i],ncc[(i+1)%4],ncc[(i+2)%4]]

    def __init__(self,data,diag=False):
        Data.__init__(self,data)
        self.diag = diag
        self.cc = self.dcc if diag else self.ncc
        self.nx = self.dnext if diag else self.nnext
        self.offs = self.doffs if diag else self.noffs

    def contour(self,pt):
        c1 = self.component(pt)
        c2 = self.filled_component(pt,c1=c1)
        xmin = min(x[0] for x in c2)
        mins = (x for x in c2 if x[0] == xmin)
        ymin = min(x[1] for x in mins)
        p = (xmin,ymin)
        assert p in c1

        for d in self.offs:
            q = (p[0]+d[0],p[1]+d[1])
            if q in c1:
                last = q
                off = (-d[0],-d[1])
                break
        else:
            dat = [p,p]
            return dat,c1,c2

        pts = [last,p]

        while len(pts) == 2 or pts[1] != pts[-1] or pts[0] != pts[-2]:
            p = pts[-1]
            for d in self.nx[off]:
                q = (p[0]+d[0],p[1]+d[1])
                if q in c1:
                    off = d
                    last = p
                    pts.append(q)
                    break
            else:
                raise ValueError(p)
        return pts,c1,c2

    def polyshape(self,pt,hsize):
        bdy,c1,c2 = self.contour(pt)
        if len(c1) <= hsize:
            return Contour(c1,c2,set())
        P = CData(bdy).bnd2outer()

        holes = []
        pts = sorted(c2-c1)
        while pts:
            p = pts[0]
            d = CData(pts)
            hole,d1,d2 = d.contour(p)
            if len(d1) > hsize:
                holes.append(CData(hole))
            pts = sorted(set(pts) - d2)
        P.reverse()
        HS = [h.bnd2outer() for h in holes]
        return Contour(c1,c2,P,HS)


    def bnd2outer(self):
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
            ret.append(p)

        p = tuple(self.data[0])
        q = p4(p)
        if len(self.data) == 2:
            assert p == tuple(self.data[1])
            return [q["nw"],q["sw"],q["se"],q["ne"],q["nw"]]

        assert tuple(self.data[0]) == tuple(self.data[-2])
        assert tuple(self.data[1]) == tuple(self.data[-1])

        ret = []
        n = len(self.data)
        for i in range(1,n-1):
            p0 = tuple(self.data[i-1])
            p1 = tuple(self.data[i])
            p2 = tuple(self.data[i+1])
            # print("P012",p0,p1,p2,end=" ")
            q = p4(p1)
            if p0 == p2: # go back
                if p1[0] > p0[0]: # R L
                    # print("RL")
                    add(ret,q["se"])
                    add(ret,q["ne"])
                    add(ret,q["nw"])
                elif p1[0] < p0[0]: # L R
                    # print("LR")
                    add(ret,q["nw"])
                    add(ret,q["sw"])
                    add(ret,q["se"])
                elif p1[1] > p0[1]: # D U
                    # print("DU")
                    add(ret,q["sw"])
                    add(ret,q["se"])
                    add(ret,q["ne"])
                elif p1[1] < p0[1]: # U D
                    # print("UD")
                    add(ret,q["ne"])
                    add(ret,q["nw"])
                    add(ret,q["sw"])
            elif p0[0]+p2[0] == 2*p1[0] and p0[1]+p2[1] == 2*p1[1]: #go straight
                # print("**")
                pass
            elif p1[0] < p0[0] and p2[1] < p1[1]: # L U
                # print("LU")
                add(ret,q["ne"])
            elif p1[1] < p0[1] and p2[0] > p1[0]: # U R
                # print("UR")
                add(ret,q["se"])
            elif p1[0] > p0[0] and p2[1] > p1[1]: # R D
                # print("RD")
                add(ret,q["sw"])
            elif p1[1] > p0[1] and p2[0] < p1[0]: # D L
                # print("DL")
                add(ret,q["nw"])
            elif p1[0] < p0[0] and p2[1] > p1[1]: # L D
                # print("LD")
                add(ret,q["nw"])
                add(ret,q["sw"])
            elif p1[1] < p0[1] and p2[0] < p1[0]: # U L
                # print("UL")
                add(ret,q["ne"])
                add(ret,q["nw"])
            elif p1[0] > p0[0] and p2[1] < p1[1]: # R U
                # print("RU")
                add(ret,q["se"])
                add(ret,q["ne"])
            elif p1[1] > p0[1] and p2[0] > p1[0]: # D R
                # print("DR")
                add(ret,q["sw"])
                add(ret,q["se"])
            else:
                raise ValueError(p0,p1,p2)
        add(ret,ret[0])
        return ret

    def component(self,pt):
        assert not self.empty

        conn = 2 if self.diag else 1
        d0 = self.maxs[0]-self.mins[0]+1
        d1 = self.maxs[1]-self.mins[1]+1
        m0,m1 = self.mins
        x = pt[0] - m0
        y = pt[1] - m1
        a = np.array(d0*d1*[0])
        a=a.reshape(d0,d1)
        for i,j in self.sdat:
            a[(i-m0,j-m1)] = 1
        l=label(a,connectivity=conn)
        clabel = l[x,y]
        return {(i+m0,j+m1)
                for i in range(d0) for j in range(d1)
                if l[i,j] == clabel}

    def filled_component(self,pt,c1=None):
        if self.empty:
            return set()
        print("C1")
        c1 = CData(self.component(pt)) if c1 is None else CData(c1)
        if c1.empty:
            return set()
        box = make_box(c1.mins-1,c1.maxs+2)
        print("C2a")
        c2 = CData(box - c1.sdat)
        print("C2b")
        s = c2.component(c1.mins-1)
        print("C3")
        return box-s
