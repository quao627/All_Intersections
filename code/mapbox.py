import requests
import math
import shutil
import cv2
from PIL import Image
import matplotlib.pyplot as plt

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def get_sat_image(lat, lon, zoom=19, output="img.jpeg"):
    username = "mapbox"
    style_id = "satellite-streets-v11"
    width = 1024
    height = 1024
    token = "pk.eyJ1IjoicXVhbzYyNyIsImEiOiJjbDcweHgxejYwaDF2M25udHhhbnF0OGF5In0.H_PomUU7ptHoRMe0GLy5RA"
    url = f"https://api.mapbox.com/styles/v1/{username}/{style_id}/static/{lon},{lat},{zoom}/{width}x{height}@2x?access_token={token}"
    response = requests.get(url, stream=True)
    with open(output, 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)

def show_image(file):
    img = cv2.imread(file)
    plt.figure(figsize=(20,20))
    plt.imshow(img,cmap='gray')