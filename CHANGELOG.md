# Changelog

Notable changes to the Python client for the Helmholtz coil rig.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-06-22

Adapted the client to the whole rig (HelmMagControl + HelmCalib + SensorCastFMX),
with gyroscope support and unified orchestration.

### Added
- **`sensorcast_client.py`** — `SensorCastClient` class (UDP) that subscribes with
  `HOLA` and parses the phone's JSON: accelerometer, magnetometer and **gyroscope**
  ([SensorCastFMX](https://github.com/ebalvis/SensorCastFMX) version). Methods
  `read`, `readings`, `mag_avg`, `acc_avg`, `gyro_avg`. Backward compatible with
  the B4A version (no gyroscope → `gyro = None`).
- **`helmholtz_rig.py`** — `HelmholtzRig` facade composing `WanptekClient`,
  `HelmCalibClient` and `SensorCastClient`, with **automatic calibration**
  (`auto_calibrate`): sweeps currents, measures the field with the phone and fits
  `B = M·I + b` in HelmCalib. Includes `measure_field`, `solve`, `set_field`, `all_off`.
- **`test_rig.py`** — orchestrator test without hardware (in-memory doubles that
  simulate the rig as `B = M0·I + b0`); verifies the sweep, the recovery of
  `M0`/`b0` and the `set_field` round-trip.

### Changed
- **`read_android_sensor.py`** — rewritten on top of `SensorCastClient`: now parses
  the JSON (previously printed raw text) and also shows the gyroscope.
- **`README.md`** — documents SensorCastFMX/gyroscope, `SensorCastClient` and
  `HelmholtzRig`; the example JSON includes `gyroscope`.

## [0.1.0] - 2025-09-25

Initial version of the client.

### Added
- **`wanptek_control.py`** — `WanptekClient`: TCP control of the supplies via
  HelmMagControl (port 4444).
- **`helmcalib_control.py`** — `HelmCalibClient`: high-level TCP control of
  HelmCalib (port 4445): status, coil/sensor connection, model, solver, field
  programming and point-based calibration.
- **`read_android_sensor.py`** — basic UDP script to read the Android sensor.
- **`test_wanptek.py`**, **`test_helmcalib.py`** — usage examples.

[0.2.0]: https://github.com/ebalvis/python-client-for-helmholtz-rig/releases/tag/v0.2.0
[0.1.0]: https://github.com/ebalvis/python-client-for-helmholtz-rig/releases/tag/v0.1.0
