import energycalc
import unittest
import json

class EnergyCalcTestCase(unittest.TestCase):

    def setUp(self):
        self.app = energycalc.app.test_client()

    def tearDown(self):
        pass

    def api(self, hsp0, hsp1, csp0, csp1, climate):
        url = '/api?climate=%s&hsp0=%s&hsp1=%s&csp0=%s&csp1=%s' \
                % (climate, hsp0, hsp1, csp0, csp1)
        rv = self.app.get(url)
        return rv
        
    def test_root(self):
        rv = self.app.get('/')
        assert rv.status_code == 200

    def test_api(self):
        rv = self.app.get('/api?climate=San%20Francisco&hsp0=70&hsp1=68&csp0=72&csp1=76.3')
        assert rv.status_code == 200

    def test_basecase(self):
        rv = self.api(70, 70, 72, 72, 'San Francisco')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        nonzero_cooling = filter(lambda v: v != 0.0, data['cooling']['chart_data'].values())
        assert len(nonzero_cooling) == 0, "Cooling savings are not zero"
        nonzero_heating = filter(lambda v: v != 0.0, data['heating']['chart_data'].values())
        assert len(nonzero_heating) == 0, "Cooling savings are not zero"

    def test_hsp_truncate(self):
        hsp0, hsp1, csp0, csp1 = 73, 71, 74, 74
        setpoints = (hsp0, hsp1, csp0, csp1)
        rv = self.api(hsp0, hsp1, csp0, csp1, 'San Francisco')
        assert rv.status_code == 200
        data = json.loads(rv.data)
        nonzero_cooling = filter(lambda v: v != 0.0, data['cooling']['chart_data'].values())
        assert len(nonzero_cooling) == 0, \
                "Cooling savings are not zero: hsp0=%s, hsp1=%s, csp0=%s, csp1=%s" % setpoints
        nonzero_heating = filter(lambda v: v != 0.0, data['heating']['chart_data'].values())
        assert len(nonzero_heating) == 0, \
                "Heating savings are not zero: hsp0=%s, hsp1=%s, csp0=%s, csp1=%s" % setpoints

if __name__ == '__main__':
    unittest.main()
