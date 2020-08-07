from flask import Flask, request, render_template, jsonify
from model import EnergyCalcModel
import pandas as pd
import json
import requests
import requests_cache

requests_cache.install_cache('sba_cache')

app = Flask(__name__)

def FtoC(f):
    return (f - 32) * 5 / 9

CLIMATE_ZONE_SUBTYPE_C = ['Alameda','Marin','Mendocino','Monterey','Napa','San Benito','San Francisco','San Luis Obispo','San Mateo','Santa Barbara','Santa Clara','Santa Cruz','Sonoma','Ventura']

CLIMATE_ZONE_MAP = {
    '1': 'Miami',
    '2': 'Phoenix',
    '3': 'Fresno',
    '3C': 'San Francisco',
    '4': 'Baltimore',
    '5': 'Chicago',
    '6': 'Duluth',
    '7': 'Duluth',
    '8': 'Duluth'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api')
def calculate():
    # curl localhost:8000/api?hsp0=21&hsp1=19&csp0=23&csp1=25&climate=Miami

    e = EnergyCalcModel()

    csp0 = FtoC(float(request.args.get('csp0')))
    csp1 = FtoC(float(request.args.get('csp1')))
    hsp0 = FtoC(float(request.args.get('hsp0')))
    hsp1 = FtoC(float(request.args.get('hsp1')))
    climate = request.args.get('climate')

    if (csp0 > csp1 or hsp0 < hsp1):
        raise InvalidUsage("Starting setpoint range not contained in adjusted setpoint range")

    # Assume an existing VAV system with sufficiently low minimums
    vintage = 'Existing'
    vav_type = 'Low'
    vav_fixed = False 

    rv = {}
    rv['heating'] = e.calculate(hsp0, hsp1, climate, vav_type, vintage, vav_fixed, False)
    rv['cooling'] = e.calculate(csp0, csp1, climate, vav_type, vintage, vav_fixed, True)

    return json.dumps(rv)

def get_climate_zone(state, county):
    df = pd.read_csv("db/climateByCounty.csv")
    countyState = county + ", " + state
    climateZone = df[df['County'] == countyState]['Climate zone'].values[0]

    return climateZone

@app.route('/climate')
def climate():
    # curl localhost:5000/climate?state=MA&city=Boston
    state = request.args.get('state')
    county = request.args.get('county')

    if county is None:
        return json.dumps({'valid': False})
    else:
        if(county in CLIMATE_ZONE_SUBTYPE_C): climate_zone = '3C'
        else: climate_zone = str(get_climate_zone(state, county))
        climate = CLIMATE_ZONE_MAP[climate_zone]
        rv = { 'valid': True, 'county': county, 'climate_zone': climate_zone, 'climate': climate } 
        return json.dumps(rv)

@app.route('/detail')
def detail():
    pass

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

if __name__ == '__main__':
    app.run()
