#-------------------------------------------------------------------------------
# Name:        sensorcast_client
# Purpose:     UDP client for SensorCast / SensorCastFMX (a wireless magnetometer
#              running on an Android phone). Subscribes with "HOLA" and receives
#              JSON with accelerometer, magnetometer and -in the FMX version- gyroscope.
#
#              JSON emitted by the phone (every ~200 ms):
#                  {"accelerometer": {"x":..,"y":..,"z":..},
#                   "magnetometer":  {"x":..,"y":..,"z":..},
#                   "gyroscope":     {"x":..,"y":..,"z":..}}   # optional (FMX only)
#
#              Backward compatible with the B4A version (no gyroscope): in that
#              case Reading.gyro is None.
#
# Author:      ebalvis
# Licence:     MIT
#-------------------------------------------------------------------------------
import socket
import json
from collections import namedtuple

Vec3 = namedtuple("Vec3", "x y z")
# A full reading from the phone. gyro may be None (legacy B4A version).
Reading = namedtuple("Reading", "acc mag gyro raw addr")


class SensorCastClient:
    """UDP subscription client for the phone's sensor server.

    Typical usage:
        with SensorCastClient("192.168.88.166") as s:
            r = s.read()                  # Reading(acc=Vec3, mag=Vec3, gyro=Vec3|None, ...)
            print(r.mag.x, r.mag.y, r.mag.z)
            bx, by, bz = s.mag_avg(k=10)  # mean of 10 magnetometer samples
    """

    def __init__(self, ip, tx_port=51042, rx_port=51043, timeout=3.0):
        self.ip = ip
        self.tx_port = tx_port      # phone port that "HOLA" is sent to
        self.rx_port = rx_port      # local port where data is received
        self.timeout = timeout
        self.sock = None

    # ---- transport ----
    def connect(self):
        """Opens the socket, listens on rx_port and subscribes by sending HOLA."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", self.rx_port))
        self.subscribe()
        return self

    def subscribe(self):
        """(Re)sends HOLA to register as a client on the phone."""
        if not self.sock:
            raise ConnectionError("Socket not open; call connect() first")
        self.sock.sendto(b"HOLA", (self.ip, self.tx_port))

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *exc):
        self.close()

    # ---- reading ----
    def read(self):
        """Blocks until a packet arrives and returns a Reading.

        Raises socket.timeout if nothing arrives within 'timeout' seconds.
        """
        if not self.sock:
            raise ConnectionError("Socket not open; call connect() first")
        data, addr = self.sock.recvfrom(4096)
        doc = json.loads(data.decode("utf-8"))
        return Reading(
            acc=self._vec(doc, "accelerometer"),
            mag=self._vec(doc, "magnetometer"),
            gyro=self._vec(doc, "gyroscope"),   # None if not present (B4A)
            raw=doc,
            addr=addr,
        )

    def readings(self):
        """Infinite generator of readings (Reading). Useful for loops."""
        while True:
            yield self.read()

    def mag_avg(self, k=10):
        """Mean of the last K magnetometer readings -> Vec3 (uT)."""
        return self._avg("mag", k)

    def acc_avg(self, k=10):
        """Mean of the last K accelerometer readings -> Vec3 (m/s^2)."""
        return self._avg("acc", k)

    def gyro_avg(self, k=10):
        """Mean of the last K gyroscope readings -> Vec3 (rad/s).

        Raises ValueError if the phone does not send gyroscope (B4A version).
        """
        return self._avg("gyro", k)

    # ---- internals ----
    def _avg(self, field, k):
        sx = sy = sz = 0.0
        n = 0
        for _ in range(k):
            v = getattr(self.read(), field)
            if v is None:
                raise ValueError("The sensor does not provide '%s'" % field)
            sx += v.x; sy += v.y; sz += v.z
            n += 1
            # keep the subscription alive during long sweeps
            if n % 25 == 0:
                self.subscribe()
        return Vec3(sx / n, sy / n, sz / n)

    @staticmethod
    def _vec(doc, key):
        d = doc.get(key)
        if not d:
            return None
        return Vec3(float(d["x"]), float(d["y"]), float(d["z"]))


# ---- command-line demo ----
if __name__ == "__main__":
    import sys
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.88.166"
    print("Subscribing to SensorCast at %s:51042 (Ctrl+C to exit)" % ip)
    try:
        with SensorCastClient(ip) as s:
            for r in s.readings():
                g = "  gyro=(%.2f %.2f %.2f)" % r.gyro if r.gyro else "  (no gyro)"
                print("acc=(%.2f %.2f %.2f)  mag=(%.2f %.2f %.2f)%s" %
                      (r.acc.x, r.acc.y, r.acc.z, r.mag.x, r.mag.y, r.mag.z, g))
    except KeyboardInterrupt:
        print("\nClosing...")
