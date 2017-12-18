from osgeo import gdal

def geotrans(path):
    ds = gdal.Open(path)
    c, a, b, f, d, e = ds.GetGeoTransform()

    def pixel2coord(col, row):
        """Returns global coordinates to pixel ulcorner using base-0 raster index"""
        xp = a * col + b * row + c #a * 0.5 + b * 0.5 + c
        yp = d * col + e * row + f #d * 0.5 + e * 0.5 + f
        return(xp, yp)
    return pixel2coord


def rgeotrans(path):
    ds = gdal.Open(path)
    c, a, b, f, d, e = ds.GetGeoTransform()

    def coord2pixel(x,y):
        """Returns global coordinates to pixel ulcorner using base-0 raster index"""
        x -= c
        y -= f

        col = e * x - b * y
        row = -d * x + a * y
        det = a*e-b*d
        return (col/det,row/det)
    return coord2pixel
