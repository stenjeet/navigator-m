# Configuration

**English** | [Русский](../ru/configuration.md)

This reference lists every YAML parameter used by the runtime nodes, together
with defaults, units and a short explanation. Parameters use SI units unless
stated otherwise.

## How parameters are loaded

Each YAML file contains one top-level section per node. The section name must
match the node name assigned by the launch file. `occupancy.yaml` uses the
`/**` wildcard because the launch file starts the same mapper twice under
different names (`occupancy_grid_ekf` and `occupancy_grid_gt`).

| File | Node section | Loaded by |
|---|---|---|
| `navigator_sim/config/motion.yaml` | `motion_node` | `simulation.launch.py` |
| `navigator_sim/config/sensors.yaml` | `uwb_model_node`, `lidar_model_node` | `simulation.launch.py` |
| `navigator_localization/config/ekf.yaml` | `ekf_node` | `simulation.launch.py`, `mapping.launch.py` |
| `navigator_slam/config/occupancy.yaml` | `/**` (all mapper instances) | `mapping.launch.py` |
| `navigator_slam/config/landmarks.yaml` | `landmark_node` | `landmarks.launch.py`, `slam.launch.py` |
| `navigator_slam/config/ekf_slam.yaml` | `ekf_slam_node` | `slam.launch.py` |

`simulation.launch.py` and `mapping.launch.py` accept alternative sensor and
EKF files through `sensors_params:=...` and `ekf_params:=...`. This is how the
scenario analysis tool runs alternative noise profiles.

ROS parameter override syntax also works:

```bash
ros2 run navigator_localization ekf_node --ros-args -p uwb_sigma:=0.10
```

## motion.yaml

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `start_x` | `1.5` | m | Initial `x` of the trajectory. |
| `start_y` | `1.5` | m | Initial `y` of the trajectory. |
| `start_yaw` | `0.0` | rad | Initial heading. |
| `side_length` | `4.0` | m | Side of the square trajectory. |
| `linear_velocity` | `0.35` | m/s | Forward speed on straight segments. |
| `angular_velocity` | `0.60` | rad/s | Turn rate at the corners. |
| `time_step` | `0.05` | s | Integration and publish step. |
| `wheel_radius` | `0.09` | m | Wheel radius for joint states. |
| `wheel_base` | `0.42` | m | Distance between the wheels. |
| `loops` | `1` | — | Number of square loops. Use `2` to exercise loop closure. |

## sensors.yaml

The file has two node sections. Both sensors use the same seed by default.

### uwb_model_node

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `random_seed` | `12025` | — | Seed for reproducible noise and dropouts. |
| `uwb_sigma` | `0.05` | m | Standard deviation of additive range noise. |
| `uwb_dropout_probability` | `0.03` | — | Probability that a range is `NaN`. |
| `uwb_biases` | `[0.02, -0.03, 0.04, 0.01]` | m | Per-anchor bias for A1..A4. |
| `uwb_rate_hz` | `10.0` | Hz | Publish rate. |
| `anchors` | not set | m | Optional flat `x, y, z` list. Omit to use `world.UWB_ANCHORS`. |
| `outage_start_s` | `0.0` | s | Start of a full UWB outage window. |
| `outage_end_s` | `0.0` | s | End of the outage window; `0.0/0.0` disables it. |

Do not write `anchors: []`. ROS cannot infer the type of an empty YAML sequence
and stores the parameter as uninitialized. Omit the key to use the default
arena layout. When changing the layout, set the same anchors in `ekf.yaml` (and
`ekf_slam.yaml` if SLAM is used).

### lidar_model_node

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `random_seed` | `12025` | — | Seed for reproducible noise and dropouts. |
| `lidar_sigma` | `0.02` | m | Standard deviation of range noise. |
| `lidar_bias` | `0.01` | m | Constant range bias. |
| `lidar_dropout_probability` | `0.01` | — | Probability of a missing reflection (`inf`). |
| `lidar_range_min` | `0.12` | m | Minimum accepted range. |
| `lidar_range_max` | `8.0` | m | Maximum accepted range. |
| `lidar_beams` | `360` | — | Beams per scan. |
| `lidar_rate_hz` | `10.0` | Hz | Publish rate. |

The lidar offset is not a sensor-model parameter: it is defined in
`world.LIDAR_OFFSET` and used by ray casting, occupancy mapping and landmark
detection.

## ekf.yaml

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `initial_x` | `1.5` | m | Initial pose estimate. |
| `initial_y` | `1.5` | m | Initial pose estimate. |
| `initial_yaw` | `0.0` | rad | Initial heading estimate. |
| `initial_std_x` | `0.10` | m | Initial 1-sigma uncertainty in `x`. |
| `initial_std_y` | `0.10` | m | Initial 1-sigma uncertainty in `y`. |
| `initial_std_yaw` | `0.0873` | rad | Initial 1-sigma uncertainty in heading (5 deg). |
| `q_x` | `1.0e-4` | m^2 | Process-noise variance per prediction step. |
| `q_y` | `1.0e-4` | m^2 | Process-noise variance per prediction step. |
| `q_yaw` | `1.0e-4` | rad^2 | Process-noise variance per prediction step. |
| `uwb_sigma` | `0.05` | m | Range noise used to build `R`; `R = uwb_sigma^2`. |
| `tag_offset` | `[-0.15, 0.12, 0.46]` | m | UWB tag position in `base_link`. |
| `use_tag_offset` | `true` | — | Apply the tag offset in the measurement model. |
| `anchor_names` | `['A1', 'A2', 'A3', 'A4']` | — | Names used in logs. |
| `anchors` | A1..A4 triples | m | Anchor positions as flat `x, y, z`. |
| `predict_rate_hz` | `20.0` | Hz | Prediction rate. |
| `path_max_poses` | `5000` | — | Maximum poses kept in `/estimate/path`. |
| `path_every_n` | `4` | — | Append every N-th prediction to the path. |
| `publish_error` | `true` | — | Publish `/estimate/error` and RMSE logs. |

`q_*` values are per prediction step. The default 20 Hz prediction timer makes
them constant in time; scale them if the timer rate changes.

## occupancy.yaml

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `scan_topic` | `/scan_noisy` | — | Lidar scan input. |
| `pose_topic` | `/estimate/odom` | — | Pose input; overridden by the launch file. |
| `map_topic` | `/map` | — | Occupancy grid output; overridden by the launch file. |
| `frame_id` | `map` | — | Frame of the output grid. |
| `resolution` | `0.05` | m/cell | Cell size. |
| `grid_min_x`, `grid_min_y` | `-0.5` | m | Lower grid bounds. |
| `grid_max_x`, `grid_max_y` | `8.5` | m | Upper grid bounds. |
| `p_occupied` | `0.70` | — | Occupied evidence probability per beam. |
| `p_free` | `0.30` | — | Free evidence probability per beam. |
| `log_odds_min` | `-2.0` | — | Lower clamp for log-odds. |
| `log_odds_max` | `3.5` | — | Upper clamp for log-odds. |
| `occupied_threshold` | `0.60` | — | Probability threshold for `100`. |
| `free_threshold` | `0.40` | — | Probability threshold for `0`. |
| `lidar_offset` | `[0.18, 0.0, 0.34]` | m | Lidar position in `base_footprint`. |
| `max_range` | `8.0` | m | Ignore longer beams. |
| `pose_tolerance` | `0.25` | s | Maximum age of a pose matched to a scan. |
| `pose_buffer_size` | `100` | — | Number of poses kept for matching. |
| `publish_rate_hz` | `1.0` | Hz | Map publish rate. |

With the default bounds and resolution the grid is `180 x 180` cells.

## landmarks.yaml

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `scan_topic` | `/scan_noisy` | — | Lidar scan input. |
| `pose_topic` | `/estimate/odom` | — | Pose used for the map; empty disables tracking. |
| `observation_topic` | `/landmarks/observations` | — | Pose-free observation output. |
| `map_topic` | `/landmarks/map` | — | Landmark map output. |
| `marker_topic` | `/landmarks/markers` | — | Marker output. |
| `frame_id` | `base_footprint` | — | Frame of observations. |
| `map_frame_id` | `map` | — | Frame of the landmark map. |
| `lidar_offset` | `[0.18, 0.0, 0.34]` | m | Lidar position in `base_footprint`. |
| `jump_threshold` | `0.15` | m | Metric floor for cluster segmentation. |
| `min_points` | `3` | — | Minimum beams in a cluster. |
| `max_points` | `25` | — | Maximum beams in a cluster. |
| `max_cluster_width` | `0.20` | m | Maximum physical cluster width. |
| `radius_min` | `0.04` | m | Minimum fitted circle radius. |
| `radius_max` | `0.25` | m | Maximum fitted circle radius. |
| `max_residual` | `0.05` | m | Maximum radial RMS residual. |
| `max_range` | `8.0` | m | Ignore farther beams. |
| `min_range` | `0.12` | m | Ignore closer beams. |
| `sigma_range` | `0.02` | m | Range noise used in observation covariance. |
| `sigma_bearing` | `0.02` | rad | Bearing noise used in observation covariance. |
| `gate` | `9.21` | — | Chi-square gate for 2-dof association (99 %). |
| `map_alpha` | `0.30` | — | Exponential moving average weight for known ids. |
| `max_landmarks` | `100` | — | Maximum tracked landmarks. |
| `min_hits` | `5` | — | Sightings required before a candidate is confirmed. |
| `tentative_gate` | `0.35` | m | Candidate association radius. |
| `max_tentative_tracks` | `200` | — | Maximum candidate buffer size. |
| `publish_rate_hz` | `2.0` | Hz | Map and marker publish rate. |

## ekf_slam.yaml

| Parameter | Default | Unit | Meaning |
|---|---:|---|---|
| `cmd_topic` | `/cmd_vel` | — | Prediction control input. |
| `observation_topic` | `/landmarks/observations` | — | Landmark observations. |
| `uwb_topic` | `/uwb/noisy_ranges` | — | UWB ranges. |
| `ground_truth_topic` | `/ground_truth/odom` | — | Ground truth for `/slam/error`. |
| `odom_topic` | `/slam/odom` | — | Pose output. |
| `path_topic` | `/slam/path` | — | Path output. |
| `landmarks_topic` | `/slam/landmarks` | — | Landmark map output. |
| `markers_topic` | `/slam/markers` | — | Marker output. |
| `error_topic` | `/slam/error` | — | Error output. |
| `frame_id` | `map` | — | Output frame. |
| `child_frame_id` | `base_footprint` | — | Robot body frame. |
| `initial_x`, `initial_y` | `1.5` | m | Initial pose estimate. |
| `initial_yaw` | `0.0` | rad | Initial heading. |
| `initial_std_x`, `initial_std_y` | `0.10` | m | Initial 1-sigma position uncertainty. |
| `initial_std_yaw` | `0.0873` | rad | Initial 1-sigma heading uncertainty. |
| `q_x`, `q_y` | `1.0e-4` | m^2 | Robot process-noise variances per step. |
| `q_yaw` | `1.0e-4` | rad^2 | Heading process-noise variance per step. |
| `predict_rate_hz` | `20.0` | Hz | Prediction rate. |
| `use_uwb` | `true` | — | Enable UWB updates. |
| `uwb_sigma` | `0.05` | m | UWB range noise. |
| `tag_offset` | `[-0.15, 0.12, 0.46]` | m | UWB tag position in `base_link`. |
| `anchors` | A1..A4 triples | m | Anchor positions as flat `x, y, z`. |
| `gate` | `9.21` | — | Chi-square association gate (99 %). |
| `sigma_range` | `0.05` | m | Landmark range model floor. |
| `sigma_bearing` | `0.05` | rad | Landmark bearing model floor. |
| `initial_landmark_std` | `0.10` | m | Minimum 1-sigma of a new landmark. |
| `max_landmarks` | `50` | — | Maximum landmarks in the joint state. |
| `min_landmark_hits` | `8` | — | Sightings required before a landmark enters the state. |
| `tentative_gate` | `0.35` | m | Candidate association radius. |
| `max_tentative_tracks` | `200` | — | Maximum candidate buffer size. |
| `path_max_poses` | `5000` | — | Maximum poses kept in `/slam/path`. |
| `path_every_n` | `4` | — | Append every N-th prediction to the path. |
| `publish_error` | `true` | — | Publish `/slam/error` and RMSE logs. |
| `publish_rate_hz` | `5.0` | Hz | Map and marker publish rate. |

## Launch arguments

| Argument | Default | Used by |
|---|---|---|
| `use_rviz` | `true` | all launch files |
| `use_localization` | `false` | `simulation.launch.py` |
| `sensors_params` | `navigator_sim/config/sensors.yaml` | `simulation.launch.py`, `mapping.launch.py` |
| `ekf_params` | `navigator_localization/config/ekf.yaml` | `simulation.launch.py`, `mapping.launch.py` |
| `pose_source` | `estimate` | `mapping.launch.py` (`estimate`, `ground_truth`, `both`) |
| `pose_topic` | `/estimate/odom` | `landmarks.launch.py` |

## RViz configuration

`navigator_description/config/navigator.rviz` is not a ROS parameter file.
It defines the fixed frame (`map`) and the initial display set: robot model,
TF, ground-truth path and pose, EKF pose and path, polygon markers, lidar
scans, occupancy maps, landmark markers and SLAM markers.

## Related documentation

- [Architecture](architecture.md) — packages, frames, topics and launch files.
- [Algorithms](algorithms.md) — what the parameters control.
- [Verification](verification.md) — tests and runtime checks.
- [Troubleshooting](troubleshooting.md) — common runtime problems.
