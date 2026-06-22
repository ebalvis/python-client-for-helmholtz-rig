#-------------------------------------------------------------------------------
# End-to-end test of the HelmCalibClient against the HelmCalib remote server.
# No hardware required: uses the nominal model and a synthetic calibration sent
# over the network.
#
# Launch HelmCalib with --remote and then: python test_helmcalib.py
#-------------------------------------------------------------------------------
from helmcalib_control import HelmCalibClient

c = HelmCalibClient("127.0.0.1", 4445)
c.connect()
print("PING   :", c.ping())
print("STATUS :", c.status())
print("NOMINAL:", c.model_nominal("A"))
print("SOLVE  :", c.solve(40, 20, 60))      # currents for B=(40,20,60)

# synthetic calibration over the network: B = M0*I + b0
M0 = [[24.8, 0.8, 0.5], [0.4, 25.3, 0.7], [0.6, 0.3, 25.1]]
b0 = [30.0, -12.0, 45.0]
amps = [(0, 0, 0), (5, 0, 0), (-5, 0, 0), (0, 5, 0), (0, -5, 0),
        (0, 0, 5), (0, 0, -5), (4, 4, 0), (4, 0, 4), (0, 4, 4),
        (3, 3, 3), (-3, 2, -4), (2, -3, 4)]
c.calib_clear()
for I in amps:
    B = [sum(M0[r][k] * I[k] for k in range(3)) + b0[r] for r in range(3)]
    c.calib_add(*I, *B)
print("COUNT  :", c.calib_count())
print("FIT RMS:", c.calib_fit())
m = c.get_model()
print("MODEL  : fitted=%s rms=%.4f M[0]=%s" %
      (m["fitted"], m["rms"], [round(x, 2) for x in m["M"][0]]))
c.close()
print("OK")
