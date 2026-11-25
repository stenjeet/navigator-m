# ROS API

**English** | [Русский](../ru/ros-api.md)

This document describes the public runtime interface of the workspace: nodes,
topics, message types, coordinate frames, parameters and launch arguments. The
document is checked against the source by `tools/check_docs.py`.

## Nodes

| Node | Default name | Package |
|---|---|---|
| Ground-truth motion | `motion_node` | `navigator_sim` |
| Polygon markers | `polygon_markers` | `navigator_sim` |
| UWB model | `uwb_model_node` | `navigator_sim` |
| Lidar model | `lidar_model_node` | `navigator_sim` |
| EKF localizer | `ekf_node` | `navigator_localization` |
| Occupancy mapper | `occupancy_grid_ekf`, `occupancy_grid_gt` | `navigator_slam` |
| Landmark detector | `landmark_node` | `navigator_slam` |
| EKF-SLAM | `ekf_slam_node` | `navigator_slam` |

The standard ROS 2 helper nodes (`robot_state_publisher`,
`joint_state_publisher`, `static_transform_publisher`) are also used by the
launch files.

## Topics

Unless stated otherwise, publishers and subscriptions use the default ROS 2
QoS profile (reliable, volatile, depth 10). `/robot_description` and
`/tf_static` are latched by their standard publishers.

| Topic | Type | Publisher | Subscribers |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | `motion_node` | `ekf_node`, `ekf_slam_node` |
| `/ground_truth/odom` | `nav_msgs/Odometry` | `motion_node` | `ekf_node`, `ekf_slam_node` |
| `/ground_truth/path` | `nav_msgs/Path` | `motion_node` | RViz |
| `/joint_states` | `sensor_msgs/JointState` | `motion_node`, `joint_state_publisher` | `robot_state_publisher` |
| `/scan_ideal` | `sensor_msgs/LaserScan` | `lidar_model_node` | RViz, tools |
| `/scan_noisy` | `sensor_msgs/LaserScan` | `lidar_model_node` | `occupancy_grid_node`, `landmark_node`, RViz, tools |
| `/uwb/ideal_ranges` | `std_msgs/Float32MultiArray` | `uwb_model_node` | tools |
| `/uwb/noisy_ranges` | `std_msgs/Float32MultiArray` | `uwb_model_node` | `ekf_node`, `ekf_slam_node` |
| `/uwb/anchors` | `visualization_msgs/MarkerArray` | `uwb_model_node` | RViz |
| `/polygon_markers` | `visualization_msgs/MarkerArray` | `polygon_markers` | RViz |
| `/estimate/odom` | `nav_msgs/Odometry` | `ekf_node` | `occupancy_grid_node`, `landmark_node`, tools, RViz |
| `/estimate/path` | `nav_msgs/Path` | `ekf_node` | RViz |
| `/estimate/error` | `geometry_msgs/Vector3Stamped` | `ekf_node` | tools |
| `/map` | `nav_msgs/OccupancyGrid` | `occupancy_grid_node` | — |
| `/map/estimate` | `nav_msgs/OccupancyGrid` | `occupancy_grid_ekf` | RViz, tools |
| `/map/ground_truth` | `nav_msgs/OccupancyGrid` | `occupancy_grid_gt` | RViz, tools |
| `/landmarks/observations` | `navigator_interfaces/LandmarkObservationArray` | `landmark_node` | `ekf_slam_node` |
| `/landmarks/map` | `navigator_interfaces/LandmarkMap` | `landmark_node` | RViz, tools |
| `/landmarks/markers` | `visualization_msgs/MarkerArray` | `landmark_node` | RViz |
| `/slam/odom` | `nav_msgs/Odometry` | `ekf_slam_node` | RViz, tools |
| `/slam/path` | `nav_msgs/Path` | `ekf_slam_node` | RViz |
| `/slam/landmarks` | `navigator_interfaces/LandmarkMap` | `ekf_slam_node` | RViz, tools |
| `/slam/markers` | `visualization_msgs/MarkerArray` | `ekf_slam_node` | RViz |
| `/slam/error` | `geometry_msgs/Vector3Stamped` | `ekf_slam_node` | tools |
| `/robot_description` | `std_msgs/String` | `robot_state_publisher` | RViz, `joint_state_publisher` |
| `/tf` | `tf2_msgs/TFMessage` | `motion_node`, `robot_state_publisher` | all TF consumers |
| `/tf_static` | `tf2_msgs/TFMessage` | `static_transform_publisher`, `robot_state_publisher` | all TF consumers |

`/map` is the default `map_topic` of the occupancy mapper. The launch file
overrides it with `/map/estimate` or `/map/ground_truth`.

## Messages

### `navigator_interfaces/LandmarkObservation`

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `range` | `float64` | m | Distance from the robot origin to the landmark centre. |
| `bearing` | `float64` | rad | Angle relative to the robot heading, in `(-pi, pi]`. |
| `radius` | `float64` | m | Radius of the fitted circular landmark. |
| `range_variance` | `float64` | m^2 | Range variance. |
| `bearing_variance` | `float64` | rad^2 | Bearing variance. |

### `navigator_interfaces/LandmarkObservationArray`

| Field | Type | Meaning |
|---|---|---|
| `header` | `std_msgs/Header` | Stamp is the scan time; frame is `base_footprint`. |
| `observations` | `navigator_interfaces/LandmarkObservation[]` | Observations from one scan. |

### `navigator_interfaces/Landmark`

| Field | Type | Unit | Meaning |
|---|---|---|---|
| `id` | `int32` | — | Stable landmark id assigned by the tracker. |
| `x` | `float64` | m | Landmark `x` in `map`. |
| `y` | `float64` | m | Landmark `y` in `map`. |
| `covariance` | `float64[4]` | m^2 | Row-major 2x2 position covariance. |

### `navigator_interfaces/LandmarkMap`

| Field | Type | Meaning |
|---|---|---|
| `header` | `std_msgs/Header` | Frame is `map`. |
| `landmarks` | `navigator_interfaces/Landmark[]` | Known landmarks. |

## Coordinate frames

| Frame | Parent | Published by |
|---|---|---|
| `map` | — | Fixed world frame. |
| `odom` | `map` | `static_transform_publisher` (identity). |
| `base_footprint` | `odom` | `motion_node` (ground truth). |
| `base_link` | `base_footprint` | `robot_state_publisher`. |
| `front_panel_link` | `base_link` | `robot_state_publisher`. |
| `left_wheel_link` | `base_link` | `robot_state_publisher`. |
| `right_wheel_link` | `base_link` | `robot_state_publisher`. |
| `front_caster_link` | `base_link` | `robot_state_publisher`. |
| `rear_caster_link` | `base_link` | `robot_state_publisher`. |
| `lidar_link` | `base_link` | `robot_state_publisher`. |
| `uwb_tag_link` | `base_link` | `robot_state_publisher`. |
| `computer_link` | `base_link` | `robot_state_publisher`. |

`ekf_node` and `ekf_slam_node` publish poses on topics but do not broadcast TF.
The simulator keeps `map -> odom` fixed, so the map and odometry frames coincide.

## Parameters

Every runtime parameter is documented with its default value in
[Configuration](configuration.md). The parameter namespaces are:

| Node | Parameter file |
|---|---|
| `motion_node` | `navigator_sim/config/motion.yaml` |
| `uwb_model_node`, `lidar_model_node` | `navigator_sim/config/sensors.yaml` |
| `ekf_node` | `navigator_localization/config/ekf.yaml` |
| `occupancy_grid_node` | `navigator_slam/config/occupancy.yaml` |
| `landmark_node` | `navigator_slam/config/landmarks.yaml` |
| `ekf_slam_node` | `navigator_slam/config/ekf_slam.yaml` |

## Launch arguments

| Launch file | Argument | Default |
|---|---|---|
| `display.launch.py` | `use_rviz` | `true` |
| `simulation.launch.py` | `use_rviz` | `true` |
| `simulation.launch.py` | `use_localization` | `false` |
| `simulation.launch.py` | `sensors_params` | `navigator_sim/config/sensors.yaml` |
| `simulation.launch.py` | `ekf_params` | `navigator_localization/config/ekf.yaml` |
| `localization.launch.py` | `use_rviz` | `true` |
| `mapping.launch.py` | `use_rviz` | `true` |
| `mapping.launch.py` | `pose_source` | `estimate` |
| `mapping.launch.py` | `sensors_params` | `navigator_sim/config/sensors.yaml` |
| `mapping.launch.py` | `ekf_params` | `navigator_localization/config/ekf.yaml` |
| `landmarks.launch.py` | `use_rviz` | `true` |
| `landmarks.launch.py` | `pose_topic` | `/estimate/odom` |
| `slam.launch.py` | `use_rviz` | `true` |

## Services and actions

The workspace does not expose any ROS services or actions. All runtime
interaction uses topics and TF.

## Verification

The API document and the documentation pairs are checked by:

```bash
python3 tools/check_docs.py
```

The checker verifies topic names, parameter names, launch arguments, message
files and fields, and the structural parity of every English/Russian document
pair.

## Related documentation

- [Architecture](architecture.md) — data flow and launch composition.
- [Configuration](configuration.md) — parameter defaults.
- [Verification](verification.md) — runtime checks.
