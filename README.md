# Navigator-M

**English** | [Русский](README.ru.md)

![ROS 2 Jazzy](https://img.shields.io/badge/ROS%202-Jazzy-22314E)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A ROS 2 workspace for simulation, localization and SLAM of the autonomous
differential-drive Navigator-M robot. The project combines a deterministic
polygon simulator, UWB and lidar measurement models, EKF localization, an
occupancy grid, landmark detection and joint EKF-SLAM.

## Features

- Simulation of an 8 × 8 m arena with obstacles, UWB anchors and landmarks.
- Ground-truth motion along a square trajectory and wheel odometry.
- UWB range and lidar scan models with noise, bias and dropouts.
- EKF localization from ranges to UWB anchors.
- Log-odds occupancy grid built from lidar scans.
- Landmark detector, data association and candidate confirmation.
- Joint EKF-SLAM: robot pose and landmark map in a single filter.
- Tools for localization metrics, map comparison and scenario analysis.
- 197 unit tests that run without a ROS installation.

## Requirements

- Ubuntu 24.04, or Windows with WSL 2 and Ubuntu 24.04.
- ROS 2 Jazzy: `ros-jazzy-desktop`, `ros-dev-tools`,
  `ros-jazzy-joint-state-publisher`.
- For plotting: `python3-numpy`, `python3-matplotlib`.

A step-by-step WSL 2, Ubuntu and ROS 2 setup is described in
[`docs/en/wsl-setup.md`](docs/en/wsl-setup.md).

## Quick start

```bash
git clone <repository-url> navigator-m
cd navigator-m

source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash

./run.sh
```

`./run.sh` builds the workspace and starts the full simulation with RViz. For a
headless run:

```bash
./run.sh use_rviz:=false
```

## Launch

| Command | Starts |
|---|---|
| `./run.sh` | Full simulation: motion, UWB, lidar, map and RViz. |
| `./run.sh use_rviz:=false` | The same without the graphical interface. |
| `ros2 launch navigator_bringup display.launch.py` | Static view of the robot and polygon. |
| `ros2 launch navigator_bringup localization.launch.py` | Simulation and EKF localization. |
| `ros2 launch navigator_bringup mapping.launch.py` | Occupancy grid from the EKF estimate. |
| `ros2 launch navigator_bringup mapping.launch.py pose_source:=both` | Two maps: one from the estimate, one from ground truth. |
| `ros2 launch navigator_bringup landmarks.launch.py` | Landmark detector and landmark map. |
| `ros2 launch navigator_bringup slam.launch.py` | Joint EKF-SLAM. |

Every launch file accepts `use_rviz` (default: `true`).
`simulation.launch.py` also accepts `use_localization`, `sensors_params` and
`ekf_params`; `mapping.launch.py` accepts `pose_source` (`estimate`,
`ground_truth` or `both`).

## Packages

| Package | Purpose |
|---|---|
| `navigator_description` | Robot URDF and RViz configuration. |
| `navigator_sim` | Polygon geometry, ground-truth motion, UWB and lidar models. |
| `navigator_localization` | EKF localization from UWB ranges. |
| `navigator_slam` | Occupancy grid, landmarks and joint EKF-SLAM. |
| `navigator_interfaces` | Messages for landmarks and landmark maps. |
| `navigator_bringup` | Launch files that assemble the full stack. |
| `tools/` | Metrics, map comparison, plots and scenario analysis. |

The packages are split by role: `navigator_description` can be reused with a
real robot, `navigator_sim` can be replaced by sensor drivers, and
`navigator_bringup` is the single place where the system is assembled.

## Main topics

| Topic | Type | Purpose |
|---|---|---|
| `/ground_truth/odom` | `nav_msgs/Odometry` | Ground-truth robot pose. |
| `/scan_noisy` | `sensor_msgs/LaserScan` | Lidar scan with noise and dropouts. |
| `/uwb/noisy_ranges` | `std_msgs/Float32MultiArray` | UWB ranges; `NaN` means dropout. |
| `/estimate/odom` | `nav_msgs/Odometry` | EKF pose estimate. |
| `/estimate/error` | `geometry_msgs/Vector3Stamped` | EKF error against ground truth. |
| `/map/estimate` | `nav_msgs/OccupancyGrid` | Map built from the EKF estimate. |
| `/map/ground_truth` | `nav_msgs/OccupancyGrid` | Reference map from ground truth. |
| `/landmarks/observations` | `navigator_interfaces/LandmarkObservationArray` | Landmarks in the robot frame. |
| `/landmarks/map` | `navigator_interfaces/LandmarkMap` | Landmark map from the tracker. |
| `/slam/odom` | `nav_msgs/Odometry` | Pose from EKF-SLAM. |
| `/slam/landmarks` | `navigator_interfaces/LandmarkMap` | Landmark map from EKF-SLAM. |
| `/slam/error` | `geometry_msgs/Vector3Stamped` | EKF-SLAM error against ground truth. |

The full node, topic and parameter reference is in
[`docs/en/ros-api.md`](docs/en/ros-api.md).

## Tests

Fast tests without ROS:

```bash
PYTHONPATH=src/navigator_slam:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_slam/test

PYTHONPATH=src/navigator_localization:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_localization/test

PYTHONPATH=src/navigator_sim:src/navigator_description \
  python3 -m unittest discover -s src/navigator_sim/test
```

Tests through `colcon`:

```bash
colcon test
colcon test-result --verbose
```

## Tools

| Command | Purpose |
|---|---|
| `./run_visualize.sh [seconds]` | Headless run and figures for the polygon, scan and UWB. |
| `./run_localization_metrics.sh [seconds]` | EKF errors and trajectory plots. |
| `./run_map_compare.sh [seconds]` | Compare maps built from ground-truth and estimated poses. |
| `./run_analysis.sh [--quick]` | Scenario analysis of localization and map accuracy. |
| `python3 tools/check_docs.py` | Check the ROS API docs and English/Russian parity. |

All outputs are written to `results/`, which is excluded from git. Saved data
can be re-rendered with `--replot` in the corresponding tool.

## Documentation

- [`docs/README.md`](docs/README.md) — documentation language index.
- [`docs/en/README.md`](docs/en/README.md) — English documentation index.
- [`docs/en/usage.md`](docs/en/usage.md) — launch commands, scripts and manual runs.
- [`docs/en/ros-api.md`](docs/en/ros-api.md) — public ROS API: nodes, topics,
  messages, frames, parameters and launch arguments.
- [`docs/en/architecture.md`](docs/en/architecture.md) — packages, data flow, frames
  and topics.
- [`docs/en/configuration.md`](docs/en/configuration.md) — YAML parameters and launch
  arguments.
- [`docs/en/algorithms.md`](docs/en/algorithms.md) — EKF, occupancy grid, landmark
  detection and EKF-SLAM.
- [`docs/en/verification.md`](docs/en/verification.md) — tests, runtime checks,
  expected results and known limitations.
- [`docs/en/troubleshooting.md`](docs/en/troubleshooting.md) — common runtime
  problems.
- [`docs/en/wsl-setup.md`](docs/en/wsl-setup.md) — Windows + WSL 2 + ROS 2 Jazzy setup.
- [`LICENSE`](LICENSE) — MIT license.

## License

This project is distributed under the MIT license. See [`LICENSE`](LICENSE) for
details.
