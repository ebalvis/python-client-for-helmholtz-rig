# python-client-for-helmholtz-rig

# Helmholtz Control Suite

This repository contains a Python software suite designed to remotely control a
Helmholtz-coil magnetic field generation system and to receive sensor telemetry
from an Android device.

The complete system is made up of several parts working together:

1.  **Control Server (BHC2000 / HelmMagControl - Delphi)**: A Windows desktop application that directly drives three Wanptek power supplies to generate the magnetic field.
2.  **Sensor Server (SensorCast - Android)**: An Android app that reads the device's accelerometer, magnetometer (and gyroscope, in the FMX version) and broadcasts them over the network.
3.  **HelmCalib (Lazarus/FPC and Delphi)**: Calibration and open-loop field programming application, with its own high-level remote server.
4.  **Client Suite (Python)**: This repository. Contains the libraries and scripts to talk to the servers, enabling automation and remote control of the whole system.

-----

## System Architecture

The project follows a distributed client-server architecture:

  * **Control PC (Python)**: Acts as the brain of the system. Runs the Python scripts that send commands and receive data.
      * `wanptek_control.py`: Connects over **TCP** to the Control Server to adjust voltages, currents and toggle the supplies on/off.
      * `sensorcast_client.py`: Subscribes over **UDP** to the Sensor Server to receive motion and magnetic field data in real time.
      * `helmcalib_control.py`: Connects over **TCP** to the **HelmCalib** server for high-level calibration and field programming.
      * `helmholtz_rig.py`: Ties the three pieces together and adds automatic calibration.
  * **Lab PC (Delphi)**: Runs the supply control application, physically connected to the power supplies. Listens for commands through its built-in TCP server.
  * **Mobile Device (Android)**: Runs the `SensorCast` app, acting as a wireless IMU, sending its readings over UDP to subscribed clients.

-----

## Components

### 1. Control Server: BHC2000 / HelmMagControl (Delphi)

Desktop application that bridges the network and the hardware.

  * **Remote API**: Implements a **TCP server** (default `4444`) accepting simple text commands: `PING`, `SET V<channel> <voltage>`, `SET I<channel> <current>`, `OUT <channel> ON|OFF`, `GET V|I|P <channel>`, `READ ALL`, `ALL OFF`.

### 2. Sensor Server: SensorCast (B4A) / SensorCastFMX (Delphi)

Android app that turns the phone into a wireless sensor. Two versions exist: the
original **B4A** one (accelerometer + magnetometer) and
[**SensorCastFMX**](https://github.com/ebalvis/SensorCastFMX) in **Delphi FireMonkey**,
which also adds a **gyroscope** and 3D visualization.

  * A client subscribes by sending a UDP `HOLA` to the phone's port **51042**; the server sends a **JSON** packet every \~200 ms to port **51043**.
  * **Data format (JSON)** — `gyroscope` only in the FMX version (optional):
    ```json
    {
      "accelerometer": { "x": 1.23, "y": 0.45, "z": 9.81 },
      "magnetometer":  { "x": 30.1, "y": -15.6, "z": 22.8 },
      "gyroscope":     { "x": 0.01, "y": -0.02, "z": 0.00 }
    }
    ```

### 3. HelmCalib — calibration and field programming (high level)

[HelmCalib](https://github.com/ebalvis/HelmCalib) fits the `B = M·I + b` model and
programs the field in open loop. It exposes a **TCP server** (default `4445`,
enable it in the *Connection* tab or start the app with `-remote`) with the same
text-protocol style. Commands: `PING`, `STATUS`, `CONNECT COILS|SENSOR`,
`GET MAG`, `GET MAGAVG <k>`, `MODEL NOMINAL A|B`, `LOAD/SAVE PROFILE`, `GET MODEL`,
`SOLVE bx by bz`, `SETFIELD bx by bz`, `SETCURRENTS i1 i2 i3`, `FIELDOFF`,
`CALIB CLEAR|ADD|COUNT|FIT`.

### 4. Client Suite (Python)

  * **`wanptek_control.py`** — `WanptekClient`: low-level supply control (HelmMagControl, TCP 4444).
  * **`helmcalib_control.py`** — `HelmCalibClient`: high-level HelmCalib control (TCP 4445).
  * **`sensorcast_client.py`** — `SensorCastClient`: UDP client for the phone sensor; parses JSON with accelerometer, magnetometer and **gyroscope** (SensorCastFMX).
  * **`helmholtz_rig.py`** — `HelmholtzRig`: **facade tying the three pieces together** with automatic calibration.
  * **`read_android_sensor.py`** — sensor demo (uses `SensorCastClient`).
  * **`test_wanptek.py`**, **`test_helmcalib.py`**, **`test_rig.py`** — examples and tests (`test_rig.py` needs no hardware).

> Version history in [CHANGELOG.md](CHANGELOG.md).

-----

## HelmCalibClient (high level)

```python
from helmcalib_control import HelmCalibClient

c = HelmCalibClient("127.0.0.1", 4445)
c.connect()

c.model_nominal("A")                 # catalog model (or load_profile / calib_*)
sol = c.solve(40, 20, 60)            # currents for B=(40,20,60) uT, without sending
print(sol["I"], sol["saturated"])

# with the supplies connected:
c.connect_coils("127.0.0.1", 4444)
c.set_field(40, 20, 60)              # computes and SENDS the currents
c.field_off()
c.close()
```

Full calibration from Python (measured I→B points):

```python
c.calib_clear()
for I, B in points:                  # B measured with the magnetometer
    c.calib_add(*I, *B)
rms = c.calib_fit()                  # fits the model, returns the RMS residual
```

Methods: `ping`, `status`, `help`, `connect_coils/sensor`, `disconnect_*`,
`get_mag`, `get_mag_avg`, `read_all`, `model_nominal`, `load_profile`,
`save_profile`, `get_model`, `solve`, `set_field`, `set_currents`, `field_off`,
`calib_clear/add/count/fit`. `test_helmcalib.py` is an end-to-end test
(no hardware required: nominal model + synthetic calibration over the network).

-----

## SensorCastClient (phone sensor)

Reads the phone's magnetometer/accelerometer/gyroscope over UDP. Supports the FMX
version (with gyroscope) and the legacy B4A one (`gyro` will be `None`).

```python
from sensorcast_client import SensorCastClient

with SensorCastClient("192.168.88.166") as s:   # wlan0 IP shown by the app
    r = s.read()                                 # Reading(acc, mag, gyro|None, raw, addr)
    print(r.mag.x, r.mag.y, r.mag.z)
    bx, by, bz = s.mag_avg(k=10)                 # mean of 10 magnetometer samples
```

Methods: `connect`, `subscribe`, `read`, `readings` (generator), `mag_avg`,
`acc_avg`, `gyro_avg`, `close`. Run `python sensorcast_client.py <ip>` as a demo.

-----

## HelmholtzRig (the three pieces combined)

Facade composing `WanptekClient` + `HelmCalibClient` + `SensorCastClient` that
automates calibration: sweeps currents, measures the field with the phone and
fits `B = M·I + b` in HelmCalib.

```python
from helmholtz_rig import HelmholtzRig

rig = HelmholtzRig(coils_host="10.1.1.50",       # HelmMagControl (optional)
                   calib_host="127.0.0.1",       # HelmCalib --remote
                   sensor_ip="192.168.88.166")   # SensorCastFMX (wlan0)
with rig:
    rms = rig.auto_calibrate(settle=2.0, k=15)   # sweep + fit -> RMS (uT)
    rig.set_field(40, 20, 60)                    # program target B
    rig.all_off()                                # turn off field and supplies
```

`auto_calibrate` flow: for each current triple → HelmCalib applies it to the
coils (`SETCURRENTS`) → wait (`settle`) → the phone measures the mean field
(`mag_avg`) → accumulate the point `(I, B)` (`CALIB ADD`) → finally `CALIB FIT`.
