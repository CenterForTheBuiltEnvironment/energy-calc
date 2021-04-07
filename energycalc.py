from flask import Flask, request, render_template, jsonify
from model import EnergyCalcModel
import json
import requests_cache
import pandas as pd

requests_cache.install_cache('sba_cache')

app = Flask(__name__)

def f_to_c(f):
    return (f - 32) * 5 / 9

f = open('db/climate_zones.json', 'r')
ASHRAE_DATA = json.load(f)
f.close()

CLIMATE_ZONE_MAP = {
    '1A': 'Miami',
    '1B': 'Miami',
    '2A': 'Phoenix',
    '2B': 'Phoenix',
    '3A': 'Fresno',
    '3B': 'Fresno',
    '3C': 'San Francisco',
    '4A': 'Baltimore',
    '4B': 'Baltimore',
    '4C': 'Baltimore',
    '5A': 'Chicago',
    '5B': 'Chicago',
    '5C': 'Chicago',
    '6A': 'Duluth',
    '6B': 'Duluth',
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

    csp0 = f_to_c(float(request.args.get('csp0')))
    csp1 = f_to_c(float(request.args.get('csp1')))
    hsp0 = f_to_c(float(request.args.get('hsp0')))
    hsp1 = f_to_c(float(request.args.get('hsp1')))
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

def get_county(city, state):
    df_us = pd.read_csv("db/uscities.csv")
    df_us.city = df_us.city.str.lower()
    df_us.state_id = df_us.state_id.str.lower()

    try:
        county = df_us.loc[(df_us.city == city.lower()) & (df_us.state_id == state.lower()), "county_name"].values[
            0]
        return county
    except IndexError:
        return None

def get_climate_zone(state, county):
    state_data = list(filter(lambda s: s['state'] == state.upper(), ASHRAE_DATA)).pop()
    exception = list(filter(lambda ex: ex['county'] == county, state_data['exceptions']))
    if exception:
        return exception[0]['climate_zone']
    else:
        return state_data['climate_zone']

@app.route('/climate')
def climate():
    # curl localhost:5000/climate?state=MA&city=Boston
    state = request.args.get('state')
    city = request.args.get('city')
    county = get_county(city, state)
    if county is None:
        return json.dumps({'valid': False})
    else:
        climate_zone = get_climate_zone(state, county)
        climate = CLIMATE_ZONE_MAP[climate_zone]
        rv = { 'valid': True, 'county': county, 'climate_zone': climate_zone, 'climate': climate } 
        return json.dumps(rv)

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
    app.run(debug=True)
