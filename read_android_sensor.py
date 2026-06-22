#-------------------------------------------------------------------------------
# Name:        read_android_sensor
# Purpose:     Demo for reading the phone sensor (SensorCast / SensorCastFMX).
#              Now uses SensorCastClient, which parses the JSON and supports
#              gyroscope (FMX version) in addition to accelerometer and magnetometer.
#
#              For the old version (raw text) see the git history.
#
# Author:      ebalvis
# Licence:     MIT
#-------------------------------------------------------------------------------
from sensorcast_client import SensorCastClient

# Phone IP (the one shown by the app, wlan0 interface)
SERVER_IP = "192.168.88.166"

if __name__ == "__main__":
    print(f"Subscribing to SensorCast at {SERVER_IP}:51042 (Ctrl+C to exit)")
    try:
        with SensorCastClient(SERVER_IP) as s:
            for r in s.readings():
                g = ("  gyro=(%.2f %.2f %.2f)" % r.gyro) if r.gyro else "  (no gyro)"
                print("acc=(%.2f %.2f %.2f)  mag=(%.2f %.2f %.2f)%s"
                      % (r.acc.x, r.acc.y, r.acc.z, r.mag.x, r.mag.y, r.mag.z, g))
    except KeyboardInterrupt:
        print("\nClosing connection...")
