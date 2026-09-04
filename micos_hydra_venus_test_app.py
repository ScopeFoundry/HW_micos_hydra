'''
Created on Aug 21, 2026

@author: Tim Kodalle
'''

from ScopeFoundry.base_app import BaseMicroscopeApp


class TestApp(BaseMicroscopeApp):

    name = "micos_hydra_venus_test_app"

    def setup(self):
        
        from ScopeFoundryHW.pi_micos_hydra_tt import MicosHydraTtHW, MicosHydraTtReadout
        self.add_hardware(MicosHydraTtHW(self, x_axis=1, y_axis=2, debug=True))
        self.add_measurement(MicosHydraTtReadout(self))



if __name__ == '__main__':
    import sys
    app = TestApp(sys.argv)
    sys.exit(app.exec_())
