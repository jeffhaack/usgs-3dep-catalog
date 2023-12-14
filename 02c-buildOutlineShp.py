# TODO: will want to run this on an Amazon server for speed

from urllib.parse import urlparse
import os
import urllib3
import shutil
from termcolor import cprint
import json
from geojson import Polygon, Feature, FeatureCollection, dump
import shapefile
import geopandas as gpd

bb_shapefile = "data/usa_1m_index.shp"
out_shapefile = "data/output.shp"
# out_shapefile2 = "data/output2.json"
tempDir = r"scratch"
errorList = []

def main():
  # Read in output shapefile so we can check DEMs that have already been done
  finishedList = []
  try:
    outGdf = gpd.read_file(out_shapefile) # read shp as geodataframe
    for feature in outGdf.iterfeatures():
      finishedList.append(feature['properties']['downloadUR'])
    cprint(f'{len(finishedList)} features already done', 'cyan')
  except Exception as e:
    cprint("Error reading in output shapefile, does it exist yet?", 'red')
    print(e)
    sys.exit()
      

  # Iterate through BB shapefile created in 01-fetchBBs.py
  print(f"Reading in {bb_shapefile}...")
  bbGdf = gpd.read_file(bb_shapefile) # read shp as geodataframe
  for feature in bbGdf.iterfeatures():
    cprint(f"Analyzing feature ID={feature['id']} ({'%.2f'%(int(feature['id'])*100/len(bbGdf))}% of {len(bbGdf)} features, {len(errorList)} errors)", 'green')
    # Get feature properties
    props = feature["properties"]   # geom = feature["geometry"] Don't need this for BB
    url = props["downloadUR"]

    # Check if it has already been processed and added to the output shapefile
    try:
      if url in finishedList:
        print(f"Already done ID {feature['id']}\n")
        continue
    except Exception as e:
      cprint("Error checking URL in finishedList - this shouldn't happen", 'red')
      print(e)
  
    # Create Temp Directory
    if os.path.exists(tempDir):
      print("Deleting Scratch Directory...\n")
      cmd = f"rm -rf {tempDir}"
      os.system(cmd)
    print("Creating Scratch Directory...\n")
    cmd = f"mkdir {tempDir}"
    os.system(cmd)

    # Download Tif file
    savePath = os.path.abspath(os.path.join(tempDir, "tempRaster.tif"))
    if not fetchFile(url, savePath):
      cprint("Unable to download file, moving on...", 'red')
      addError(url)
      continue

    # Create json file of outline
    tifGeom = makeDemPolygon(savePath, tempDir)
    if not tifGeom:
      cprint("Unable to make DEM polygon file, moving on...", 'red')
      addError(url)
      continue

    # Create new geojson file for feature
    try:
      features = []
      features.append(Feature(geometry=tifGeom, properties=props))
      feature_collection = FeatureCollection(features)
      outfile = os.path.abspath(os.path.join(tempDir, "tempOutfile.geojson"))
      with open(f'{outfile}', 'w') as f:
        dump(feature_collection, f)
    except Exception as e:
      cprint("Unable to create new geojson file, moving on...", 'red')
      addError(url)
      continue

    # Merge into shapefile
    try:
      if os.path.isfile(out_shapefile):
        print(f"Merging new feature into {out_shapefile}...")
        # Read shapefiles
        # mainShp = gpd.read_file(out_shapefile)
        mainShp = outGdf
        newShp = gpd.read_file(outfile)

        # Merge/Combine multiple shapefiles into one
        mergedShp = gpd.pd.concat([mainShp, newShp])
        
        #Export merged geodataframe into shapefile
        mergedShp.to_file(out_shapefile)
      else:
        print(f"Creating {out_shapefile}...")
        newShp = gpd.read_file(outfile)
        newShp.to_file(out_shapefile)
    except Exception as e:
      cprint("Unable to merge new data into out shapefile, moving on...", 'red')
      addError(url)
      continue
    
        
        
# add an error URL and show what's wrong
def addError(url):
  errorList.append(url)
  cprint("\n--------", 'red')
  cprint("Current errorList:", 'yellow')
  cprint(errorList, 'yellow')
  cprint("--------\n", 'red')
    

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
  try:
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
    # cprint(geom, 'cyan')
    return geom
  except Exception as e:
    cprint("Error in makeDemPolygon", 'red')
    print(e)
    return False


    # # return polyFileTemp

    # # Open the temp json file, extract the json, and create a geojson.Polygon object to return
    # f = open(polyFileTemp)
    # data = json.load(f)
    # # print(data["features"][0]["geometry"]["coordinates"])
    # poly = Polygon(data["features"][0]["geometry"]["coordinates"])
    # return poly

main()


