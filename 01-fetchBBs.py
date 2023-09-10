# use the TNM API to fetch bounding boxes for all the 1m DEMs

# a precursor to doing other stuff, maybe this is all i need

import urllib3
import json
from geojson import Polygon, Feature, FeatureCollection, dump

# this should cover Missouri as per the FIPs number - https://transition.fcc.gov/oet/info/maps/census/fips/fips.txt#:~:text=Federal%20Information%20Processing%20System%20(FIPS,on%20the%20level%20of%20geography.
# testUrl = f"https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&polyType=state&polyCode=29&max={max_items}&offset=2000"

max_items = 945        # max return items (1000 is the max that will be returned anyway)
paginating = True
offset = 0
features = []
outfile = "data/usa_1m_index.geojson"

while paginating:

    # Just Missouri
    # testUrl = f"https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&polyType=state&polyCode=29&max={max_items}&offset={offset}"

    # All 1m DEMs
    testUrl = f"https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&max={max_items}&offset={offset}"

    http = urllib3.PoolManager()
    r = http.request('GET', testUrl)
    if r.status != 200:
        print(f"ERROR reaching {testUrl}")
    else:
        # parse json:
        try:
            jsonData = json.loads(r.data)
        except Exception as e:
            print(e)
            print(r.data)
            offset += 1     # this except seems to handle occasional api errors, at the expense of dropping a few items
            continue
            
        # all the items
        items = jsonData["items"]

        # record total items
        totalItemCount = int(jsonData["total"])

        for i in items:
            bb = i["boundingBox"]
            # print(i)
            poly = Polygon([[(bb["minX"], bb["maxY"]), (bb["maxX"], bb["maxY"]), (bb["maxX"], bb["minY"]), (bb["minX"], bb["minY"]), (bb["minX"], bb["maxY"])]])
            # print(poly)

            # Remove some attributes that aren't particularly helpful            
            del i["moreInfo"]
            del i["sourceName"]
            del i["sourceOriginName"]
            del i["extent"]
            del i["downloadURLRaster"]
            del i["downloadLazURL"]
            del i["datasets"]
            del i["bestFitIndex"]
            del i["body"]
            del i["processingUrl"]

            features.append(Feature(geometry=poly, properties=i))

        if offset + 1000 < totalItemCount:
            offset += max_items
            print(f"Completed {offset} of {totalItemCount} records...")
        else:
            print(f"Completed {totalItemCount} records")
            paginating = False

        r.release_conn()

feature_collection = FeatureCollection(features)
with open(f'{outfile}', 'w') as f:
    dump(feature_collection, f)