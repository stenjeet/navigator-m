# Verification Guide

**English** | [Русский](../ru/verification.md)

This guide describes how to verify the Navigator-M stack: automated tests,
static checks, runtime smoke tests, expected output and known limitations.

All commands are run from the repository root. Prepare the environment first:

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

A `ros2 launch` command occupies its terminal. Run `ros2 topic`, `ros2 node`
and `tf2_echo` commands in a second terminal with the same environment.

## Test matrix

| Area | Command | Expected |
|---|---|---|
| Localization | `PYTHONPATH=src/navigator_localization:src/navigator_sim python3 -m unittest discover -s src/navigator_localization/test -v` | 12 tests, OK |
| SLAM and analysis | `PYTHONPATH=src/navigator_slam:src/navigator_sim python3 -m unittest discover -s src/navigator_slam/test -v` | 177 tests, OK |
| Simulation geometry | `PYTHONPATH=src/navigator_sim:src/navigator_description python3 -m unittest discover -s src/navigator_sim/test -v` | 8 tests, OK |
| Python syntax | `python3 -m py_compile $(find src tools -name '*.py')` | no errors |
| Documentation | `python3 tools/check_docs.py` | API and EN/RU docs consistent |
| ROS packages | `colcon test && colcon test-result --verbose` | all packages pass |
| Environment | `ros2 doctor` | no critical problems |

The pure-Python tests do not import `rclpy` or ROS messages, so they run on a
machine without ROS. The total is 197 tests: 177 in `navigator_slam`, 12 in
`navigator_localization` and 8 in `navigator_sim`.

## Static checks

The test suite also verifies the static scene:

- URDF links, joints and sensor mounting offsets;
- polygon geometry, obstacle clearances and arena bounds;
- scene palette and landmark definitions;
- consistency between `world.py`, the URDF and the lidar model.

Run the complete static check with:

```bash
PYTHONPATH=src/navigator_sim:src/navigator_description \
  python3 -m unittest discover -s src/navigator_sim/test -v
```

## Runtime checks

### Simulation and robot description

```bash
ros2 launch navigator_bringup simulation.launch.py use_rviz:=false
```

In a second terminal:

```bash
ros2 node list
ros2 topic hz /ground_truth/odom     # ~20 Hz
ros2 topic hz /scan_ideal            # ~10 Hz
ros2 topic hz /uwb/noisy_ranges      # ~10 Hz
ros2 run tf2_ros tf2_echo map base_footprint
```

Expected: six nodes without the localization node; `map -> odom ->
base_footprint` is published; the pose moves along the square
`(1.5, 1.5) -> (5.5, 1.5) -> (5.5, 5.5) -> (1.5, 5.5) -> (1.5, 1.5)` at
`v = 0.35 m/s` and `omega = 0.60 rad/s`.

Static display of the robot and polygon:

```bash
ros2 launch navigator_bringup display.launch.py use_rviz:=false
ros2 topic echo --once --qos-durability transient_local /robot_description | head
ros2 topic echo --once /polygon_markers | head
```

### EKF localization

```bash
ros2 launch navigator_bringup localization.launch.py use_rviz:=false
```

In a second terminal:

```bash
ros2 topic hz /estimate/odom          # ~20 Hz
ros2 topic echo --once /estimate/odom
ros2 topic echo --once /estimate/error   # x, y, yaw
```

Expected: the estimate follows ground truth with a position error of a few
centimetres on noisy UWB ranges. The heading is not observable from a single
UWB tag at rest; it is corrected during turns.

Metrics and plots:

```bash
./run_localization_metrics.sh          # 62 s
./run_localization_metrics.sh 90       # 90 s
```

Outputs: `results/result_localization_trajectory.png`,
`results/result_localization_error.png` and RMSE in the console.

### Occupancy mapping

```bash
ros2 launch navigator_bringup mapping.launch.py use_rviz:=false pose_source:=both
```

In a second terminal:

```bash
ros2 topic hz /map/estimate                 # ~1 Hz
ros2 topic echo --once /map/estimate        # 180 x 180, data -1/0/100
ros2 topic echo --once /map/ground_truth
```

Expected: two `nav_msgs/OccupancyGrid` maps with resolution `0.05 m` and
values `-1` (unknown), `0` (free) and `100` (occupied). The map built from the
EKF estimate should match the ground-truth map within a few centimetres.

Map comparison:

```bash
./run_map_compare.sh
```

Outputs: `results/result_map_compare.png`, occupied-cell IoU, agreement and
mean/max distance between occupied cells. Both maps use the same scans, so the
difference reflects pose error only.

### Landmark detection

```bash
ros2 launch navigator_bringup landmarks.launch.py use_rviz:=false
```

In a second terminal:

```bash
ros2 topic hz /landmarks/observations       # ~10 Hz
ros2 topic echo --once /landmarks/observations
ros2 topic echo --once /landmarks/map       # ids and covariances
ros2 topic echo --once /landmarks/markers
```

Expected: 1-4 observations per scan in the `base_footprint` frame and a stable
landmark map with four confirmed landmarks after a full loop. A candidate is
confirmed only after several consistent sightings, so wall corners do not
become permanent landmarks.

Detector check without localization error:

```bash
ros2 launch navigator_bringup landmarks.launch.py \
  pose_topic:=/ground_truth/odom use_rviz:=false
```

### EKF-SLAM

```bash
ros2 launch navigator_bringup slam.launch.py use_rviz:=false
```

In a second terminal:

```bash
ros2 topic hz /slam/odom                 # ~20 Hz
ros2 topic echo --once /slam/landmarks   # four landmarks with ids
ros2 topic echo --once /slam/error       # error against ground truth
```

Expected: four landmarks with stable ids and a pose error in the centimetre
range after loop closure.

Loop-closure unit test:

```bash
PYTHONPATH=src/navigator_slam:src/navigator_sim python3 -m unittest \
  src.navigator_slam.test.test_ekf_slam.TestLoopClosure.test_double_loop_closes_and_keeps_the_ids -v
```

The test drives two loops, verifies that the landmark count remains four and
that no duplicate ids appear.

Runtime loop-closure check: set `loops: 2` in
`navigator_sim/config/motion.yaml` and run `slam.launch.py`. After the second
loop, `/slam/landmarks` must keep the same four ids.

### Scenario analysis

```bash
./run_analysis.sh --quick          # 3 scenarios, 30 s each
./run_analysis.sh                  # 10 scenarios, 62 s each
python3 tools/analysis.py --replot # no ROS, from saved npz
```

Outputs:

| File | Contents |
|---|---|
| `results/analysis/summary.md` | RMSE, IoU, map distances and generated findings |
| `results/analysis/summary.csv` | The same metrics in machine-readable form |
| `results/analysis_rmse.png` | Pose and heading RMSE by scenario |
| `results/analysis_maps.png` | IoU and map distance by scenario |
| `results/analysis/analysis_data.npz` | Data for `--replot` |

Reference output from a `./run_analysis.sh --quick` run with a 3 s warm-up:

| Scenario | RMSE pos [m] | RMSE yaw [deg] | max \|e\| [m] | IoU occupied | Mean dist [m] |
|---|---|---|---|---|---|
| baseline | 0.039 | 1.19 | 0.100 | 0.337 | 0.027 |
| uwb_sigma_0.10 | 0.045 | 1.36 | 0.101 | 0.321 | 0.027 |
| dropout_0.25 | 0.040 | 1.14 | 0.096 | 0.382 | 0.026 |

The exact values depend on timing and platform, but the order of magnitude
should be stable: a few centimetres of position RMSE and about one degree of
heading RMSE.

## Acceptance checklist

- [ ] `colcon build --symlink-install` reports six packages.
- [ ] The three test suites pass: 197 tests in total.
- [ ] `py_compile` and `colcon test` finish without errors.
- [ ] Simulation publishes ground truth, UWB, lidar and TF at the expected rates.
- [ ] Localization publishes `/estimate/odom` and a bounded `/estimate/error`.
- [ ] Mapping produces `180 x 180` grids for both pose sources.
- [ ] Landmark detection publishes observations and four stable map landmarks.
- [ ] EKF-SLAM publishes `/slam/odom`, four landmarks and a bounded error.
- [ ] `./run_analysis.sh --quick` writes the summary, CSV and both figures.
- [ ] No generated file is required for the build; `results/` is local only.

## Known limitations

- **Heading from UWB.** A single UWB tag at rest constrains position only. The
  heading is corrected by motion and turns; this is a property of the model,
  not a defect.
- **Shared scans in map comparison.** Both maps use the same lidar scans, so
  their difference isolates pose error and does not measure scan noise.
- **ROS wrapper coverage.** Unit tests cover the pure mathematical modules.
  The ROS nodes are verified by launch files and topic checks, not by unit
  tests.
- **No collision physics.** Collisions are not simulated. The polygon geometry
  is verified to keep at least `0.45 m` clearance from the trajectory.
- **TF ownership.** Only `motion_node` publishes `odom -> base_footprint`.
  Localization and SLAM publish poses on topics and do not broadcast TF.
- **UWB anchors and lidar.** Radio anchors are not part of the lidar geometry;
  they are visible only as markers.
- **Landmark latency.** Observations are applied at the current filter pose
  without interpolation to the scan timestamp. At `0.35 m/s` this introduces a
  few centimetres of error.
- **Process noise.** `Q` is defined per prediction step and is not scaled by
  `dt`. At the default 20 Hz timer this is a constant per-step noise.
- **UWB biases.** The sensor model includes per-anchor biases, while the filter
  assumes zero bias, so part of the systematic error remains uncompensated.
- **Discrete time.** The simulator uses fixed timer steps and does not use
  `/clock`. Trajectory geometry is deterministic, but callback delays can
  slightly shift time alignment between runs.
- **Analysis scope.** The scenario table varies UWB noise, dropouts, outages
  and anchor layout; lidar noise is fixed at `0.02 m`.
- **Generated artifacts.** Figures and metrics under `results/` are not tracked
  by git and must be regenerated locally.
