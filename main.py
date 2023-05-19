from flask import Flask, request, render_template, jsonify
from flask_wtf import FlaskForm
from wtforms import SelectField
from model import EnergyCalcModel
import json
import requests_cache
import pandas as pd
import os

SECRET_KEY = os.urandom(32)

requests_cache.install_cache("sba_cache")

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


def f_to_c(tmp_f):
    return (tmp_f - 32) * 5 / 9


f = open("db/climate_zones.json", "r")
ASHRAE_DATA = json.load(f)
f.close()

df_us = pd.read_csv("db/uscities.csv")
# todo allow the user to select minimum population
df_us = df_us[df_us.population > 100000]
default_state_id = "NY"

CLIMATE_ZONE_MAP = {
    "1A": "Miami",
    "1B": "Miami",
    "2A": "Phoenix",
    "2B": "Phoenix",
    "3A": "Fresno",
    "3B": "Fresno",
    "3C": "San Francisco",
    "4A": "Baltimore",
    "4B": "Baltimore",
    "4C": "Baltimore",
    "5A": "Chicago",
    "5B": "Chicago",
    "5C": "Chicago",
    "6A": "Duluth",
    "6B": "Duluth",
    "7": "Duluth",
    "8": "Duluth",
}


@app.route("/")
def index():
    form = Form()

    city_choices = df_us.loc[df_us.state_id == default_state_id, "city"]

    form.city.choices = [(city, city) for city in city_choices]

    return render_template("index.html", form=form)


@app.route("/city/<state>")
def city(state):
    city_choices = df_us.loc[df_us.state_id == state, "city"]

    city_array = []
    for city in city_choices:
        city_object = {"id": city, "name": city}
        city_array.append(city_object)

    return jsonify({"cities": city_array})


class Form(FlaskForm):

    state_choices = df_us[["state_id", "state_name"]].drop_duplicates().sort_index()
    state_choices = list(zip(state_choices["state_id"], state_choices["state_name"]))

    state = SelectField(
        "state",
        choices=state_choices,
    )

    city_choices = df_us.loc[df_us.state_id == default_state_id, "city"]

    city = SelectField("state", choices=[(city, city) for city in city_choices])


@app.route("/api")
def calculate():
    # curl localhost:8000/api?hsp0=21&hsp1=19&csp0=23&csp1=25&climate=Miami

    e = EnergyCalcModel()

    csp0 = f_to_c(float(request.args.get("csp0")))
    csp1 = f_to_c(float(request.args.get("csp1")))
    hsp0 = f_to_c(float(request.args.get("hsp0")))
    hsp1 = f_to_c(float(request.args.get("hsp1")))
    _climate = request.args.get("climate")

    if csp0 > csp1 or hsp0 < hsp1:
        raise InvalidUsage(
            "Starting set point range not contained in adjusted set point range"
        )

    # Assume an existing VAV system with sufficiently low minimums
    vintage = "Existing"
    vav_type = "Low"
    vav_fixed = False

    rv = {
        "heating": e.calculate(
            hsp0, hsp1, _climate, vav_type, vintage, vav_fixed, False
        ),
        "cooling": e.calculate(
            csp0, csp1, _climate, vav_type, vintage, vav_fixed, True
        ),
    }

    return json.dumps(rv)


def get_county(city, state):
    try:
        county = df_us.loc[
            (df_us.city == city) & (df_us.state_id == state),
            "county_name",
        ].values[0]
        return county
    except IndexError:
        return None


def get_climate_zone(state, county):
    state_data = list(filter(lambda s: s["state"] == state.upper(), ASHRAE_DATA)).pop()
    exception = list(
        filter(lambda ex: ex["county"] == county, state_data["exceptions"])
    )
    if exception:
        return exception[0]["climate_zone"]
    else:
        return state_data["climate_zone"]


@app.route("/climate")
def climate():
    # curl localhost:5000/climate?state=MA&city=Boston
    state = request.args.get("state")
    city = request.args.get("city")
    county = get_county(city, state)
    if county is None:
        return json.dumps({"valid": False})
    else:
        climate_zone = get_climate_zone(state, county)
        _climate = CLIMATE_ZONE_MAP[climate_zone]
        rv = {
            "valid": True,
            "county": county,
            "climate_zone": climate_zone,
            "climate": _climate,
        }
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
        rv["message"] = self.message
        return rv


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)

