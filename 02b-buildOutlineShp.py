# TODO: will want to run this on an Amazon server for speed

from urllib.parse import urlparse
import os
import urllib3
import shutil
import json
from geojson import Polygon, Feature, FeatureCollection, dump
import shapefile
import geopandas as gpd

bb_shapefile = "data/usa_1m_index.shp"
out_shapefile = "data/output.json"
tempDir = r"scratch"

def main():

    # Iterate through BB shapefile created in 01-fetchBBs.py
    print(f"Reading in {bb_shapefile}...")
    bbGdf = gpd.read_file(bb_shapefile) # read shp as geodataframe
    for feature in bbGdf.iterfeatures():
        print(f"Analyzing feature ID={feature['id']} (total {len(bbGdf)} features)")
        # Get feature properties
        props = feature["properties"]   # geom = feature["geometry"] Don't need this for BB
        url = props["downloadUR"]

        # Check if it has already been processed and added to the output shapefile
        try:
            outGdf = gpd.read_file(
                out_shapefile,
                where=f"dlUrl='{url}'",
            )
            if len(outGdf) > 1:
                print("There may be an issue here")
            elif len(outGdf) == 1:
                print(f"Already done {url}")
                continue
            else:
                print(f"Continuing with {url}")
        except:
            print(f"Looks like {out_shapefile} hasn't been created yet, continuing...")
        
        # Probably need to close the shapefile here for safety?? TODO?
        
        # Create Temp Directory
        if not os.path.exists(tempDir):
            cmd = f"mkdir {tempDir}"
            os.system(cmd)

        # Download Tif file
        savePath = os.path.abspath(os.path.join(tempDir, "tempRaster.tif"))
        fetchFile(url, savePath)

        # Create json file of outline
        tifGeom = makeDemPolygon(savePath, tempDir)
        #print(tifGeom)

        # Create new geojson file for feature
        features = []
        features.append(Feature(geometry=tifGeom, properties=props))
        feature_collection = FeatureCollection(features)
        outfile = os.path.abspath(os.path.join(tempDir, "tempOutfile.geojson"))
        with open(f'{outfile}', 'w') as f:
            dump(feature_collection, f)

        # Merge into shapefile
        if os.path.isfile(out_shapefile):
            print(f"Merging new feature into {out_shapefile}...")
            # Read shapefiles
            mainShp = gpd.read_file(out_shapefile)
            newShp = gpd.read_file(outfile)

            # Merge/Combine multiple shapefiles into one
            mergedShp = gpd.pd.concat([mainShp, newShp])
            
            #Export merged geodataframe into shapefile
            mergedShp.to_file(out_shapefile)
        else:
            print(f"Creating {out_shapefile}...")
            newShp = gpd.read_file(outfile)
            newShp.to_file(out_shapefile)
        
        # Delete Temp Directory
        print("Deleting Scratch Directory...\n")
        cmd = f"rm -rf {tempDir}"
        os.system(cmd)


    

# Downloads a file and saves it
def fetchFile(url, savePath):
    print(f"Fetching {url}...")
    http = urllib3.PoolManager()
    with http.request('GET', url, preload_content=False) as resp, open(savePath, 'wb') as out_file:
        if resp.status != 200:
            print(f"ERROR reaching {url}")
            resp.release_conn()
            return False
        else:
            # Save the output file
            shutil.copyfileobj(resp, out_file)
            resp.release_conn()
            print(f"Saved as {savePath}")
            return True

# Takes a Raster file path and scratch directory as input, and returns a geojson.Polygon object
def makeDemPolygon(rasterFilePath, scratchDir):
    # Use gdal_translate to make a temporary, 1-bit temp file
    print(f"Converting raster to single bit...")
    rasterFilePathTemp = os.path.abspath(os.path.join(scratchDir, "tempTif.tif"))
    cmd = f"gdal_translate -of GTiff -ot Byte -co NBITS=1 {rasterFilePath} {rasterFilePathTemp}"
    os.system(cmd)

    # Convert the temp raster to a polygon and save as shp
    print(f"Creating polygon outline of raster in temporary shapefile")
    polyFileTemp = os.path.abspath(os.path.join(scratchDir, "tempPoly.shp"))    # CRS isn't read correctly on geojson
    # polyFileTemp = os.path.abspath(os.path.join(scratchDir, "tempPoly.shp"))
    cmd = f"gdal_polygonize.py {rasterFilePathTemp} {polyFileTemp}"
    os.system(cmd)

    # Open the temp json file, convert to EPSG:4326, and return the geometry
    tempGdf = gpd.read_file(polyFileTemp) # read shp as geodataframe
    tempGdf = tempGdf.to_crs('EPSG:4326')
    feature = next(tempGdf.iterfeatures())
    geom = feature["geometry"]
    return geom


    # # return polyFileTemp

    # # Open the temp json file, extract the json, and create a geojson.Polygon object to return
    # f = open(polyFileTemp)
    # data = json.load(f)
    # # print(data["features"][0]["geometry"]["coordinates"])
    # poly = Polygon(data["features"][0]["geometry"]["coordinates"])
    # return poly

main()


