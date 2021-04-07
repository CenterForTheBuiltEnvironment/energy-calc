import pickle
from gen_db import __pickle_file__
from scipy.interpolate import interp1d
from numpy import isnan


class EnergyCalcModel:

    __climates__ = [
        "Miami",
        "Phoenix",
        "Fresno",
        "San Francisco",
        "Baltimore",
        "Chicago",
        "Duluth",
    ]
    __vav_types__ = ["High", "Low"]
    __vintages__ = ["Existing", "New"]

    def __init__(self):
        file = open(__pickle_file__, "rb")
        self.db = pickle.load(file)
        self.f_terminal_heating = None
        self.f_central_heating = None
        self.f_cooling = None
        self.f_fans = None
        self.f_hvac = None

    def filter_db(self, climate_zone, vav_type, vintage, vav_fixed):
        db = list(filter(lambda r: r["climate"] == climate_zone, self.db))
        system_type = vav_type + vintage + ("VAVFixed" if vav_fixed else "VAVAuto")
        db = list(filter(lambda r: r["type"] == system_type, db))
        return db

    def pluck_and_interpolate(self, db):
        hsp = list(map(lambda r: float(r["heating_sp"]), db))
        csp = list(map(lambda r: float(r["cooling_sp"]), db))
        x = hsp
        x[11:] = csp[11:]

        terminal_heating = [x["terminal_heating"] for x in db]
        self.f_terminal_heating = interp1d(x, terminal_heating)
        self.f_central_heating = interp1d(x, [x["central_heating"] for x in db])
        self.f_cooling = interp1d(x, [x["cooling"] for x in db])
        self.f_fans = interp1d(x, [x["fans"] for x in db])
        self.f_hvac = interp1d(x, [x["hvac"] for x in db])

    def calculate(
        self,
        sp0,
        sp1,
        climate_zone,
        vav_type,
        vintage,
        vav_fixed,
        cool_side,
        verbose=False,
    ):

        if cool_side:
            # cooling side
            # new method: truncate
            if sp0 < 22.225:
                sp0 = 22.225
            if sp1 < 22.225:
                sp1 = 22.225
            if sp0 > 30:
                sp0 = 30
            if sp1 > 30:
                sp1 = 30
        else:
            # heating side
            if sp0 > 21.1:
                sp0 = 21.1
            if sp1 > 21.1:
                sp1 = 21.1
            if sp0 < 17.6:
                sp0 = 17.6
            if sp1 < 17.6:
                sp1 = 17.6

        db = self.filter_db(climate_zone, vav_type, vintage, vav_fixed)
        self.pluck_and_interpolate(db)

        if verbose:
            increasing = "increasing" if (sp0 < sp1) else "decreasing"
            cooling_sp = "cooling" if cool_side else "heating"
            print(
                "Savings from %s the %s from %s to %s"
                % (increasing, cooling_sp, sp0, sp1)
            )
            print("-" * 40)

        return self.savings(sp0, sp1, verbose)

    def savings(self, sp0, sp1, verbose=False, component_savings=False):
        terminal_heating0 = self.f_terminal_heating(sp0)
        terminal_heating1 = self.f_terminal_heating(sp1)
        central_heating0 = self.f_central_heating(sp0)
        central_heating1 = self.f_central_heating(sp1)
        cooling_0 = self.f_cooling(sp0)
        cooling_1 = self.f_cooling(sp1)
        fans_0 = self.f_fans(sp0)
        fans_1 = self.f_fans(sp1)
        hvac_0 = self.f_hvac(sp0)
        hvac_1 = self.f_hvac(sp1)

        terminal_heating_savings_per = (
            100 * (terminal_heating0 - terminal_heating1) / hvac_0
        )
        central_heating_savings_per = (
            100 * (central_heating0 - central_heating1) / hvac_0
        )
        cooling_savings_per = 100 * (cooling_0 - cooling_1) / hvac_0
        fan_savings_per = 100 * (fans_0 - fans_1) / hvac_0
        hvac_savings_per = 100 * (hvac_0 - hvac_1) / hvac_0

        natural_gas_0 = terminal_heating0 + central_heating0
        natural_gas_1 = terminal_heating1 + central_heating1
        electric_0 = cooling_0 + fans_0
        electric_1 = cooling_1 + fans_1

        natural_gas_savings_per = 100 * (natural_gas_0 - natural_gas_1) / natural_gas_0
        electric_savings_per = 100 * (electric_0 - electric_1) / electric_0

        if verbose:
            print("total hvac savings: %s %%" % hvac_savings_per)
            print("breakdown:")
            print("terminal heating savings: %s %%" % terminal_heating_savings_per)
            print("central heating savings: %s %%" % central_heating_savings_per)
            print("cooling savings: %s %%" % cooling_savings_per)
            print("fan savings: %s %%" % fan_savings_per)
            print("natural gas savings: %s %%" % natural_gas_savings_per)
            print("electricity savings: %s %%" % electric_savings_per)

        rv = {
            "chart_data": {
                "terminal_heating_savings_per": terminal_heating_savings_per,
                "central_heating_savings_per": central_heating_savings_per,
                "cooling_savings_per": cooling_savings_per,
                "fan_savings_per": fan_savings_per,
            },
            "table_data": {
                "electric_savings_per": electric_savings_per,
                "natural_gas_savings_per": natural_gas_savings_per,
            },
        }

        if component_savings:
            rv["component_savings"] = {}
            rv["component_savings"]["terminal_heating_component_savings_per"] = (
                100 * (terminal_heating0 - terminal_heating1) / terminal_heating0
            )
            rv["component_savings"]["central_heating_component_savings_per"] = (
                100 * (central_heating0 - central_heating1) / central_heating0
            )
            rv["component_savings"]["cooling_component_savings_per"] = (
                100 * (cooling_0 - cooling_1) / cooling_0
            )
            rv["component_savings"]["fan_component_savings_per"] = (
                100 * (fans_0 - fans_1) / fans_0
            )

        for k in rv["chart_data"]:
            if isnan(rv["chart_data"][k]):
                rv["chart_data"][k] = 0.0
            if rv["chart_data"][k] < 0:
                rv["chart_data"][k] = 0.0

        for k in rv["table_data"]:
            if isnan(rv["table_data"][k]):
                rv["table_data"][k] = 0.0
            if rv["table_data"][k] < 0:
                rv["table_data"][k] = 0.0

        return rv


if __name__ == "__main__":
    e = EnergyCalcModel()
    e.calculate(22.77, 22.77, "Duluth", "Low", "Existing", False, False, verbose=True)
