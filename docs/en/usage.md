# Detailed Guide

**English** | [Русский](../ru/usage.md)

An extended guide to launching the stack, topics, parameters and algorithms.
The short start page is in [README](../../README.md).

ROS 2 workspace of the **navigator** project: robot model, test-site map,
ground-truth square trajectory, UWB range and lidar scan models, UWB EKF
localization, occupancy grid, landmark detection and EKF-SLAM.

The primary environment is **Ubuntu 24.04 with ROS 2 Jazzy**; Windows 11 via
WSL 2 is also supported. Step-by-step installation from scratch:
[`wsl-setup.md`](wsl-setup.md). The code uses only `rclpy`, standard
messages and `launch`, so it also builds on ROS 2 Humble (Ubuntu 22.04).

## Quick start

```bash
cd ~/navigator-m                   # the project must live on the Linux filesystem, not in /mnt/c
./run.sh use_rviz:=false            # build + headless simulation; Ctrl+C to stop
./run.sh                            # same, but with the RViz window (Windows 11 via WSLg)
```

Next, verify in a second terminal (see [Verification](#verification)) or capture
the figures: `./run_visualize.sh`.

## Structure

The workspace contains six ROS 2 packages under `src/`, offline tools under
`tools/`, and documentation under `docs/`. Package responsibilities, runtime
data flow, coordinate frames and the complete topic list are described in
[Architecture](architecture.md).

## Requirements

- Ubuntu 24.04 + ROS 2 Jazzy: `ros-jazzy-desktop` (includes RViz2), `ros-dev-tools` (colcon), `ros-jazzy-joint-state-publisher` (for `display.launch.py`).
- For figures: `python3-numpy`, `python3-matplotlib`.

## Build (once)

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Expected: `Summary: 6 packages finished` (`navigator_description`,
`navigator_sim`, `navigator_bringup`, `navigator_localization`,
`navigator_slam`, `navigator_interfaces`).

## Scripts

| Command | What it does |
|---|---|
| `./run.sh [launch arguments]` | `colcon build --symlink-install`, `source install/setup.bash`, `ros2 launch navigator_bringup simulation.launch.py`. Arguments are passed through to the launch file: `./run.sh use_rviz:=false`. Rebuilds on every run (a couple of seconds) so stale code is never started. |
| `./run_visualize.sh [seconds]` | Starts `tools/visualize.py` in the background, brings up the headless simulation, records data (62 s by default, or `./run_visualize.sh 90`), renders PNGs into `results/`, then shuts the simulation down. **Requires an existing `install/` build** — run `./run.sh` or `colcon build` first after code changes. |
| `python3 tools/visualize.py --replot` | Re-renders the plots from the saved `results/plot_data.npz` without starting the simulation. Additional options: `--duration N`, `--out DIR`. |
| `./run_localization_metrics.sh [seconds]` | Headless run with the EKF, recording `/ground_truth/odom` and `/estimate/odom` (62 s by default), PNGs and RMSE in `results/`. |
| `python3 tools/localization_metrics.py --replot` | Re-renders the metrics from `results/localization_data.npz`. |
| `./run_map_compare.sh [seconds]` | Headless run with two mappers (ground-truth pose and EKF estimate), map comparison, PNGs, distance and IoU in `results/`. |
| `python3 tools/map_compare.py --replot` | Re-renders the map comparison from `results/map_compare_data.npz`. |
| `./run_analysis.sh [seconds] [--quick]` | Runs the scenarios in sequence (UWB σ, dropouts, UWB outage window, anchor layouts) and writes a table and plots into `results/`. |
| `python3 tools/analysis.py --replot` | Re-renders the analysis table and plots from `results/analysis/analysis_data.npz`. |

All shell scripts source the ROS distribution from `/opt/ros/jazzy/setup.bash`;
another path can be supplied via a variable, for example
`ROS_SETUP=/opt/ros/humble/setup.bash ./run.sh`.

## Running manually

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# motion + UWB + lidar + map + RViz
ros2 launch navigator_bringup simulation.launch.py

# without graphics
ros2 launch navigator_bringup simulation.launch.py use_rviz:=false

# static display of the model and the map (no motion);
# use_rviz:=false — headless smoke test only, no window
ros2 launch navigator_bringup display.launch.py

# simulation + EKF localization
ros2 launch navigator_bringup localization.launch.py
# equivalent to:
ros2 launch navigator_bringup simulation.launch.py use_localization:=true

# occupancy grid from the EKF estimate (the EKF starts automatically)
ros2 launch navigator_bringup mapping.launch.py
# map from the ground-truth pose / both maps at once (for comparison)
ros2 launch navigator_bringup mapping.launch.py pose_source:=ground_truth
ros2 launch navigator_bringup mapping.launch.py pose_source:=both

# landmark detection and association (pose from the EKF)
ros2 launch navigator_bringup landmarks.launch.py
# EKF-SLAM (joint estimation of the pose and the landmark map)
ros2 launch navigator_bringup slam.launch.py

# detector and association with the ground-truth pose
ros2 launch navigator_bringup landmarks.launch.py pose_topic:=/ground_truth/odom
```

Every launch file has a `use_rviz` argument (default `true`);
`simulation.launch.py` accepts `use_localization`, `sensors_params` and
`ekf_params` (scenario YAML files used by the analysis), while
`mapping.launch.py` accepts `pose_source` (`estimate` by default,
`ground_truth`, `both`) and forwards `sensors_params`/`ekf_params`.

## Nodes and topics

The complete node, topic, frame and launch-composition reference is in
[Architecture](architecture.md). The main runtime topics are also summarized in
the project [README](../../README.md).

## Verification

The test matrix, runtime smoke checks, expected results and known limitations
are in [Verification](verification.md).

## Processing pipeline

- **EKF localization** turns `/cmd_vel` and `/uwb/noisy_ranges` into
  `/estimate/odom`.
- **Occupancy mapping** turns `/scan_noisy` and a pose into `/map/estimate` or
  `/map/ground_truth`.
- **Landmark detection** turns scans and a pose into `/landmarks/observations`
  and `/landmarks/map`.
- **EKF-SLAM** fuses `/cmd_vel`, UWB ranges and landmark observations into
  `/slam/odom` and `/slam/landmarks`.

Models, equations and tuning rationale are in [Algorithms](algorithms.md).

## Performance analysis

`tools/analysis.py` runs the scenarios in sequence, varying parameters through
generated YAML files (`sensors_params`/`ekf_params`), and aggregates the metrics:

| Scenario | What changes |
|---|---|
| `baseline` | nominal `sensors.yaml` and `ekf.yaml` |
| `uwb_sigma_0.02/0.10/0.20` | UWB σ in the model **and** in the filter |
| `uwb_mismatch_r_low` | model 0.10 m, filter 0.05 m (optimistic R) |
| `dropout_0.10/0.25` | UWB dropout probability |
| `outage_20_40` | all ranges `NaN` from second 20 to second 40 |
| `anchors_wide` / `anchors_compact` | test-site corners / anchors near the start |

Metrics: RMSE and maximum pose error (`/estimate/error`), IoU of occupied cells
and the mean distance between the `/map/estimate` and `/map/ground_truth` maps.
EKF-SLAM accuracy is checked by a separate `slam.launch.py` run (`/slam/error`
and the RMSE in the `ekf_slam_node` log) and is not part of the scenario table.
Results: `results/analysis/summary.md` (table + automatic conclusions),
`results/analysis/summary.csv`, `results/analysis_rmse.png`,
`results/analysis_maps.png`.

```bash
./run_analysis.sh --quick      # baseline + σ 0.10 + dropout 0.25, 30 s each (~3 min)
./run_analysis.sh              # full table, 62 s each (~13 min)
python3 tools/analysis.py --replot   # table and plots without starting the simulation
```

The first 3 s after the first `/estimate/error` message are discarded as warm-up
(`--warmup`, 3 s by default): the EKF starts from a fixed initial pose while the
robot is already moving, and that transient would otherwise produce a large
`max |e|` unrelated to the steady-state accuracy.

## Stopping

`Ctrl+C` in the launch terminal. If processes are left behind after an abnormal
interruption:

```bash
pkill -9 -f lib/navigator_sim
pkill -9 -f lib/navigator_slam
pkill -9 -f /opt/ros/jazzy/lib/robot_state_publisher
pkill -9 -f /opt/ros/jazzy/lib/tf2_ros/static_transform_publisher
```

## Parameters

All YAML files, parameter defaults and launch arguments are listed in
[Configuration](configuration.md).

## Generating figures

```bash
./run_visualize.sh        # headless run ~62 s, PNGs in results/
./run_visualize.sh 90     # longer recording
```

| File | What it shows |
|------|---------------|
| `results/result_map.png` | top view: test site, ground-truth trajectory, accumulated lidar map |
| `results/result_scan.png` | one scan: ideal and noisy points in the lidar frame |
| `results/result_uwb.png` | A1–A4 ranges: ideal vs noise + bias + dropouts |
| `results/result_localization_*.png` | EKF localization: trajectory and errors |
| `results/result_map_compare.png` | occupancy grid from the ground-truth and estimated pose + differences |
| `results/analysis_rmse.png` | localization RMSE across the analysis scenarios |
| `results/analysis_maps.png` | IoU and map distance across the analysis scenarios |
| `results/analysis/summary.md` | metrics table and automatic conclusions |

The raw run data is saved to `results/plot_data.npz`. Re-render without starting
the simulation:

```bash
source /opt/ros/jazzy/setup.bash && source install/setup.bash
python3 tools/visualize.py --replot
```

## RViz

`navigator_description/config/navigator.rviz` defines a top-down view: the robot
model, TF, the ground-truth trajectory and the EKF estimate (`/estimate/odom`,
`/estimate/path`), the test-site markers, both lidar scans (`/scan_ideal`,
`/scan_noisy`), the occupancy grid maps (`/map/estimate` enabled,
`/map/ground_truth` disabled by default), as well as `/slam/path`, `/slam/odom`,
`/slam/markers` and `/landmarks/markers`, disabled by default — enabling them via
the checkbox is enough when running `landmarks.launch.py` or `slam.launch.py`.
The Fixed Frame is `map`. On Windows 11 the RViz window opens through WSLg; on a
headless machine you can take screenshots through a virtual display:

```bash
sudo apt install -y xvfb imagemagick
Xvfb :99 -screen 0 1600x1000x24 &
export DISPLAY=:99
ros2 launch navigator_bringup simulation.launch.py
import -window root rviz.png
```

## Troubleshooting

Common problems with sourcing, build, DDS, RViz, topics and analysis tools are
covered in [Troubleshooting](troubleshooting.md).
