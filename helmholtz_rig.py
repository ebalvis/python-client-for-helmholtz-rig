#-------------------------------------------------------------------------------
# Name:        helmholtz_rig
# Purpose:     Facade that ties the THREE pieces of the Helmholtz coil rig into a
#              single control object, and offers automatic calibration.
#
#                - WanptekClient    (HelmMagControl, TCP 4444): per-axis X/Y/Z supplies
#                - HelmCalibClient  (HelmCalib,      TCP 4445): model B=M*I+b, solver
#                - SensorCastClient (SensorCastFMX,  UDP):       phone magnetometer
#
#              Automatic calibration flow (uses all three at once):
#                  for each target current triple:
#                      HelmCalib applies the currents to the coils  (SETCURRENTS)
#                      wait for the field to settle
#                      the phone measures the mean field            (mag_avg)
#                      accumulate the point (I, B) in HelmCalib       (CALIB ADD)
#                  fit the model                                      (CALIB FIT)
#
# Author:      ebalvis
# Licence:     MIT
#-------------------------------------------------------------------------------
import time

from wanptek_control import WanptekClient
from helmcalib_control import HelmCalibClient
from sensorcast_client import SensorCastClient


# Default current sweep (A): origin + axes +/- + non-coplanar diagonals.
# >=4 non-coplanar points are required to fit B=M*I+b.
DEFAULT_SWEEP = [
    (0, 0, 0),
    (5, 0, 0), (-5, 0, 0),
    (0, 5, 0), (0, -5, 0),
    (0, 0, 5), (0, 0, -5),
    (4, 4, 0), (4, 0, 4), (0, 4, 4),
    (3, 3, 3), (-3, 2, -4), (2, -3, 4),
]


class HelmholtzRig:
    """Orchestrates supplies (HelmMagControl), calibration (HelmCalib) and sensor (SensorCast).

    Example:
        rig = HelmholtzRig(coils_host="10.1.1.50", calib_host="127.0.0.1",
                           sensor_ip="192.168.88.166")
        rig.connect()
        rms = rig.auto_calibrate()          # full sweep + fit
        print("RMS:", rms, "uT")
        rig.set_field(40, 20, 60)           # program target B (open loop)
        rig.all_off()
        rig.close()
    """

    def __init__(self, coils_host=None, calib_host="127.0.0.1", sensor_ip=None,
                 coils_port=4444, calib_port=4445,
                 sensor_tx=51042, sensor_rx=51043):
        self.coils = WanptekClient(coils_host, coils_port) if coils_host else None
        self.calib = HelmCalibClient(calib_host, calib_port)
        self.sensor = SensorCastClient(sensor_ip, sensor_tx, sensor_rx) if sensor_ip else None

    # ---- lifecycle ----
    def connect(self):
        """Connects to the configured pieces (HelmCalib is mandatory)."""
        self.calib.connect()
        if self.coils:
            self.coils.connect()
        if self.sensor:
            self.sensor.connect()
        return self

    def close(self):
        for part in (self.sensor, self.coils, self.calib):
            try:
                if part:
                    part.close()
            except Exception:
                pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    # ---- measurement ----
    def measure_field(self, k=15):
        """Mean field measured by the phone -> (bx, by, bz) in uT."""
        if not self.sensor:
            raise RuntimeError("No sensor configured (sensor_ip)")
        return tuple(self.sensor.mag_avg(k))

    # ---- automatic calibration ----
    def auto_calibrate(self, currents=None, settle=2.0, k=15, verbose=True):
        """Sweeps 'currents', measures the field with the phone and fits B=M*I+b.

        currents: list of (i1, i2, i3) triples in amperes. Defaults to DEFAULT_SWEEP.
        settle:   seconds to wait after setting currents (field + thermal settling).
        k:        number of magnetometer samples averaged per point.
        Returns the fit residual RMS (uT).
        """
        if not self.sensor:
            raise RuntimeError("Automatic calibration requires sensor_ip")
        currents = currents or DEFAULT_SWEEP

        self.calib.calib_clear()
        for idx, (i1, i2, i3) in enumerate(currents, 1):
            # HelmCalib maps the (signed) currents to the physical supplies
            self.calib.set_currents(i1, i2, i3)
            time.sleep(settle)
            bx, by, bz = self.measure_field(k)
            n = self.calib.calib_add(i1, i2, i3, bx, by, bz)
            if verbose:
                print("[%2d/%2d] I=(%6.2f %6.2f %6.2f) -> B=(%7.2f %7.2f %7.2f)  points=%d"
                      % (idx, len(currents), i1, i2, i3, bx, by, bz, n))

        self.calib.field_off()
        rms = self.calib.calib_fit()
        if verbose:
            print("Fit complete. RMS = %.3f uT" % rms)
        return rms

    # ---- field programming (open loop, via HelmCalib) ----
    def solve(self, bx, by, bz):
        """Currents needed for a target B, WITHOUT applying them."""
        return self.calib.solve(bx, by, bz)

    def set_field(self, bx, by, bz):
        """Computes currents for target B and applies them to the coils."""
        return self.calib.set_field(bx, by, bz)

    # ---- safety ----
    def all_off(self):
        """Turns off the field (HelmCalib) and the supply outputs (Wanptek)."""
        try:
            self.calib.field_off()
        finally:
            if self.coils:
                self.coils.all_off()


if __name__ == "__main__":
    # Demo: set the real IPs before running against hardware.
    rig = HelmholtzRig(coils_host=None,            # optional: HelmMagControl IP
                       calib_host="127.0.0.1",     # HelmCalib --remote
                       sensor_ip="192.168.88.166") # wlan0 IP shown by SensorCastFMX
    with rig:
        print("STATUS:", rig.calib.status())
        rms = rig.auto_calibrate(settle=2.0, k=15)
        print("RMS    :", rms, "uT")
        rig.all_off()
