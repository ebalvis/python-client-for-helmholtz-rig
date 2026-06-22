#-------------------------------------------------------------------------------
# Name:        helmcalib_control
# Purpose:     High-level TCP client for HelmCalib (calibration + open-loop field
#              programming + sensor reading). Talks to the HelmCalib remote server
#              (text protocol, one line per command, 'OK ...' / 'ERROR ...'
#              responses, UTF-8), in the style of WanptekClient.
#
# Author:      ebalvis
# Licence:     MIT
#-------------------------------------------------------------------------------
import socket


class HelmCalibError(Exception):
    """The server response started with 'ERROR ...'."""
    pass


class HelmCalibClient:
    def __init__(self, host="127.0.0.1", port=4445, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._buf = b""

    # ---- transport ----
    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        self._buf = b""

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def _readline(self):
        while b"\n" not in self._buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line.decode("utf-8").strip()

    def send_command(self, command):
        """Sends a text command and returns the raw response."""
        if not self.sock:
            raise ConnectionError("Not connected to the HelmCalib server")
        self.sock.sendall((command + "\n").encode("utf-8"))
        return self._readline()

    def _ok(self, command):
        """Like send_command, but raises HelmCalibError if the response is ERROR."""
        resp = self.send_command(command)
        if resp.startswith("ERROR"):
            raise HelmCalibError(resp)
        return resp

    # ---- general ----
    def ping(self):
        return self.send_command("PING")

    def help(self):
        return self.send_command("HELP")

    def status(self):
        """dict with the state: coils, sensor, model, rms."""
        r = self._ok("STATUS").split()
        # OK COILS on SENSOR off MODEL ready(A) RMS 0
        d = {}
        for i in range(1, len(r) - 1, 2):
            d[r[i].lower()] = r[i + 1]
        return d

    # ---- hardware connection ----
    def connect_coils(self, host, port=4444):
        return self._ok(f"CONNECT COILS {host} {port}")

    def connect_sensor(self, ip, tx=51042, rx=51043):
        return self._ok(f"CONNECT SENSOR {ip} {tx} {rx}")

    def disconnect_coils(self):
        return self._ok("DISCONNECT COILS")

    def disconnect_sensor(self):
        return self._ok("DISCONNECT SENSOR")

    # ---- sensor ----
    def get_mag(self):
        """Latest magnetometer reading (uT) -> (x, y, z)."""
        return self._parse_vec(self._ok("GET MAG"), "MAG")

    def get_mag_avg(self, k=10):
        """Mean of the last K magnetometer samples -> (x, y, z)."""
        return self._parse_vec(self._ok(f"GET MAGAVG {k}"), "MAGAVG")

    def read_all(self):
        return self._ok("READALL")

    # ---- calibration model ----
    def model_nominal(self, kind="A"):
        return self._ok(f"MODEL NOMINAL {kind}")

    def load_profile(self, path):
        return self._ok(f"LOAD PROFILE {path}")

    def save_profile(self, path):
        return self._ok(f"SAVE PROFILE {path}")

    def get_model(self):
        """dict with M (3x3 list of rows), b (x,y,z), rms, fitted."""
        toks = self._ok("GET MODEL").split()
        m = [float(x) for x in toks[2:11]]
        M = [m[0:3], m[3:6], m[6:9]]
        bi = toks.index("B")
        b = tuple(float(x) for x in toks[bi + 1:bi + 4])
        rms = float(toks[toks.index("RMS") + 1])
        fitted = toks[toks.index("FITTED") + 1] == "1"
        return {"M": M, "b": b, "rms": rms, "fitted": fitted}

    # ---- field programming (open loop) ----
    def solve(self, bx, by, bz):
        """Computes currents for a target B WITHOUT sending them. -> dict."""
        return self._parse_field(self._ok(f"SOLVE {bx} {by} {bz}"))

    def set_field(self, bx, by, bz):
        """Computes currents and SENDS them to the supplies. -> dict."""
        return self._parse_field(self._ok(f"SETFIELD {bx} {by} {bz}"))

    def set_currents(self, i1, i2, i3):
        return self._ok(f"SETCURRENTS {i1} {i2} {i3}")

    def field_off(self):
        return self._ok("FIELDOFF")

    # ---- calibration ----
    def calib_clear(self):
        return self._ok("CALIB CLEAR")

    def calib_add(self, ix, iy, iz, bx, by, bz):
        """Adds a point (currents I, measured field B). -> number of points."""
        r = self._ok(f"CALIB ADD {ix} {iy} {iz} {bx} {by} {bz}")
        return int(r.split()[-1])

    def calib_count(self):
        return int(self._ok("CALIB COUNT").split()[-1])

    def calib_fit(self):
        """Fits the model with the accumulated points. -> RMS residual (uT)."""
        return float(self._ok("CALIB FIT").split()[-1])

    # ---- parsers ----
    @staticmethod
    def _parse_vec(resp, tag):
        t = resp.split()
        i = t.index(tag)
        return tuple(float(x) for x in t[i + 1:i + 4])

    @staticmethod
    def _parse_field(resp):
        # OK I i1 i2 i3 SAT 0 ACHIEVED ax ay az
        t = resp.split()
        ii = t.index("I")
        ai = t.index("ACHIEVED")
        return {
            "I": tuple(float(x) for x in t[ii + 1:ii + 4]),
            "saturated": t[t.index("SAT") + 1] == "1",
            "achieved": tuple(float(x) for x in t[ai + 1:ai + 4]),
        }
