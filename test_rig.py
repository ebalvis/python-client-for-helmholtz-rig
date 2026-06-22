#-------------------------------------------------------------------------------
# Test of the HelmholtzRig orchestrator WITHOUT hardware.
#
# Replaces the calibration client (HelmCalib) and the sensor client (SensorCast)
# with in-memory doubles that simulate the physical rig as  B = M0*I + b0.  The
# sensor and the calibration share an "applied currents" state, so measuring the
# field reflects the currents the orchestrator just set.
#
# Verifies that HelmholtzRig.auto_calibrate():
#   - walks the whole sweep and accumulates one point per triple,
#   - measures a field consistent with the currents,
#   - fits the model recovering M0/b0 with RMS ~ 0.
#
# Usage:  python test_rig.py     (no hardware nor external dependencies required)
#-------------------------------------------------------------------------------
from helmholtz_rig import HelmholtzRig, DEFAULT_SWEEP

# Simulated "physical rig": field = M0 * I + b0
M0 = [[24.8, 0.8, 0.5], [0.4, 25.3, 0.7], [0.6, 0.3, 25.1]]
b0 = [30.0, -12.0, 45.0]


def _inv(A):
    """Inverse of an n x n matrix via Gauss-Jordan (no dependencies)."""
    n = len(A)
    M = [list(A[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        M[col] = [v / d for v in M[col]]
        for r in range(n):
            if r != col:
                f = M[r][col]
                M[r] = [a - f * b for a, b in zip(M[r], M[col])]
    return [row[n:] for row in M]


def _fit_affine(points):
    """Least-squares fit of B = M*I + b. Returns (M, b, rms)."""
    S = [[0.0] * 4 for _ in range(4)]   # sum x*xT, x = [Ix,Iy,Iz,1]
    P = [[0.0] * 4 for _ in range(3)]   # sum B*xT
    for I, B in points:
        x = [I[0], I[1], I[2], 1.0]
        for r in range(4):
            for c in range(4):
                S[r][c] += x[r] * x[c]
        for r in range(3):
            for c in range(4):
                P[r][c] += B[r] * x[c]
    Sinv = _inv(S)
    A = [[sum(P[r][k] * Sinv[k][c] for k in range(4)) for c in range(4)] for r in range(3)]
    M = [row[:3] for row in A]
    b = [row[3] for row in A]
    # residual RMS
    sq = 0.0
    n = 0
    for I, B in points:
        for r in range(3):
            pred = sum(M[r][c] * I[c] for c in range(3)) + b[r]
            sq += (pred - B[r]) ** 2
            n += 1
    rms = (sq / n) ** 0.5
    return M, b, rms


class _RigState:
    """Shared physical state: last applied currents."""
    def __init__(self):
        self.I = (0.0, 0.0, 0.0)


class FakeCalib:
    """In-memory double of HelmCalibClient."""
    def __init__(self, state):
        self.state = state
        self.points = []
        self.M = None
        self.b = None
        self.rms = None

    def connect(self): pass
    def close(self): pass
    def status(self): return {"coils": "sim", "sensor": "sim", "model": "nofit"}

    def set_currents(self, i1, i2, i3):
        self.state.I = (float(i1), float(i2), float(i3))
        return "OK"

    def field_off(self):
        self.state.I = (0.0, 0.0, 0.0)
        return "OK"

    def calib_clear(self):
        self.points = []
        return "OK"

    def calib_add(self, ix, iy, iz, bx, by, bz):
        self.points.append(((ix, iy, iz), (bx, by, bz)))
        return len(self.points)

    def calib_fit(self):
        self.M, self.b, self.rms = _fit_affine(self.points)
        return self.rms

    def solve(self, bx, by, bz):
        """I = M^-1 (B - b) with the fitted model."""
        Minv = _inv(self.M)
        d = [bx - self.b[0], by - self.b[1], bz - self.b[2]]
        I = tuple(sum(Minv[r][c] * d[c] for c in range(3)) for r in range(3))
        return {"I": I, "saturated": False, "achieved": (bx, by, bz)}

    def set_field(self, bx, by, bz):
        r = self.solve(bx, by, bz)
        self.set_currents(*r["I"])
        return r


class FakeSensor:
    """In-memory double of SensorCastClient: measures B = M0*I + b0 from the state."""
    def __init__(self, state):
        self.state = state

    def connect(self): pass
    def close(self): pass

    def mag_avg(self, k=10):
        I = self.state.I
        return tuple(sum(M0[r][c] * I[c] for c in range(3)) + b0[r] for r in range(3))


def main():
    state = _RigState()
    rig = HelmholtzRig(sensor_ip="sim")     # clients are swapped for doubles
    rig.calib = FakeCalib(state)
    rig.sensor = FakeSensor(state)
    rig.coils = None

    rms = rig.auto_calibrate(settle=0, k=1, verbose=False)
    M, b = rig.calib.M, rig.calib.b

    # ---- checks ----
    assert len(rig.calib.points) == len(DEFAULT_SWEEP), "missing sweep points"
    assert rms < 1e-6, "fit should be exact with synthetic data: %g" % rms

    err_M = max(abs(M[r][c] - M0[r][c]) for r in range(3) for c in range(3))
    err_b = max(abs(b[r] - b0[r]) for r in range(3))
    assert err_M < 1e-6 and err_b < 1e-6, "M0/b0 not recovered (M=%g b=%g)" % (err_M, err_b)

    # round-trip: program a target field and check it is reached
    target = (40.0, 20.0, 60.0)
    res = rig.set_field(*target)
    achieved = rig.measure_field(k=1)
    err_field = max(abs(achieved[i] - target[i]) for i in range(3))
    assert err_field < 1e-6, "programmed field not reached: %g" % err_field

    print("sweep points   :", len(rig.calib.points))
    print("fit RMS        : %.3e uT" % rms)
    print("error M / b    : %.3e / %.3e" % (err_M, err_b))
    print("set_field %-16s I=(%.3f %.3f %.3f)" % (str(target), *res["I"]))
    print("field achieved : (%.2f %.2f %.2f)  error=%.3e" % (*achieved, err_field))
    print("OK")


if __name__ == "__main__":
    main()
