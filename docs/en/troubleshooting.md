# Troubleshooting

**English** | [Русский](../ru/troubleshooting.md)

This guide covers the most common problems when building and running the
Navigator-M stack. Start with the diagnostics below, then use the section that
matches the symptom.

## First diagnostics

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
source install/setup.bash

ros2 doctor
ros2 pkg list | grep navigator
ros2 node list
ros2 topic list
```

Always source both the ROS distribution and the workspace in every terminal.
Most "missing package", "unknown message type" and "topic not found" problems
come from a terminal where `install/setup.bash` was not sourced.

## Environment and workspace

| Symptom | Cause | Fix |
|---|---|---|
| `ros2: command not found` | ROS is not sourced. | `source /opt/ros/jazzy/setup.bash` |
| `Package 'navigator_bringup' not found` | Workspace is not built or not sourced. | `colcon build --symlink-install` and `source install/setup.bash` |
| Custom message type is unknown | Workspace with `navigator_interfaces` is not sourced. | Source `install/setup.bash` in that terminal. |
| Commands work in one terminal only | Each terminal has its own environment. | Repeat both `source` commands. |
| Wrong ROS distribution | `ROS_SETUP` or shell environment points elsewhere. | Use `/opt/ros/jazzy/setup.bash` or set `ROS_SETUP` explicitly. |

## Build

| Symptom | Cause | Fix |
|---|---|---|
| Build is extremely slow | Workspace is inside `/mnt/c` on WSL. | Move it to the Linux filesystem, for example `~/navigator-m`. |
| `colcon build` reports missing dependencies | System or ROS dependencies are absent. | `rosdep install --from-paths src --ignore-src -r -y` |
| Python package changes are not visible | Workspace was built without symlinks. | `colcon build --symlink-install` |
| Stale behaviour after editing code | Old installation is still sourced. | Rebuild and reopen the terminal, or run `./run.sh`. |
| `setup.py` metadata warnings | Package metadata is inconsistent. | Check `package.xml` and `setup.py` in the affected package. |
| Build fails after switching ROS distro | `build/` and `install/` contain artefacts from another distro. | Remove `build/ install/ log/` and rebuild. |

## Simulation and topics

| Symptom | Cause | Fix |
|---|---|---|
| `/scan_ideal` or `/uwb/noisy_ranges` is silent | Simulation is not running. | Start `simulation.launch.py` or `./run.sh`. |
| Topic rate is zero | Node crashed or the topic is not published in this configuration. | Check the launch terminal for exceptions. |
| `/map/estimate` is missing | Mapping is not running, or `/estimate/odom` is absent. | Start `mapping.launch.py` with `pose_source:=estimate` or `both`. |
| `/map/ground_truth` is missing | Mapping runs without the ground-truth source. | Use `pose_source:=ground_truth` or `pose_source:=both`. |
| `/landmarks/observations` is silent | `landmark_node` is not running. | Start `landmarks.launch.py` or `slam.launch.py`. |
| `/slam/odom` is missing | `ekf_slam_node` is not running. | Start `slam.launch.py`; SLAM does not use `/estimate/odom`. |
| `/estimate/odom` is missing | Localization is not enabled. | Start `localization.launch.py` or `simulation.launch.py use_localization:=true`. |
| TF `map -> base_footprint` does not move | `motion_node` is not running or the wrong frame is queried. | Check `ros2 node list` and `tf2_echo map base_footprint`. |
| `NaN` in UWB ranges | A dropout is part of the sensor model. | Expected behaviour; filters skip `NaN`. |
| `inf` in lidar ranges | A missing reflection is part of the lidar model. | Expected behaviour; mapping ignores invalid beams. |

## RViz and graphics

| Symptom | Cause | Fix |
|---|---|---|
| RViz window does not open on Windows 10 | No X server or WSLg. | Use `use_rviz:=false` or configure an X server. |
| RViz opens empty | Fixed frame or displays are misconfigured. | Load `navigator_description/config/navigator.rviz`; fixed frame is `map`. |
| Robot model is missing | `robot_state_publisher` is not running or URDF failed to parse. | Check the launch log and `/robot_description`. |
| Markers are missing | `/polygon_markers` is not published. | Start the simulation or `display.launch.py`. |
| SLAM or landmark displays are off | They are disabled by default in RViz. | Enable the corresponding displays manually. |
| Headless screenshot is needed | No display is available. | Use Xvfb and `import`, or run with `use_rviz:=false` and save data from tools. |
| RViz is slow | Too many displays or a large point cloud. | Disable unused displays and reduce scan history. |

## DDS and networking

| Symptom | Cause | Fix |
|---|---|---|
| Nodes in different terminals do not see each other | Different `ROS_DOMAIN_ID` or incompatible RMW. | Export the same `ROS_DOMAIN_ID` and RMW implementation in both terminals. |
| Discovery is unreliable in a VM or WSL | Multicast or firewall restrictions. | Use the same network mode, check firewall rules, or set `ROS_LOCALHOST_ONLY=1` for local-only runs. |
| Communication works locally but not across machines | Network or firewall blocks DDS discovery. | Open the required DDS ports or use a discovery server. |
| Old nodes keep reappearing | A previous launch is still running. | Stop it with `Ctrl+C` or use the cleanup commands below. |

## Analysis tools

| Symptom | Cause | Fix |
|---|---|---|
| `run_visualize.sh` says the workspace is not built | No `install/` directory. | `colcon build --symlink-install` |
| Plotting fails on import | Missing Python packages. | `sudo apt install python3-numpy python3-matplotlib` |
| `analysis.py` reports no `/estimate/error` | EKF did not start or the startup timeout is too short. | Check the EKF launch log and increase `--startup-timeout`. |
| `map_compare.py` finds no map | Mapper was started without two pose sources. | Use `pose_source:=both`. |
| Analysis seems to hang | Scenarios run sequentially and each takes tens of seconds. | Wait for the status lines, or use `--quick`. |
| `--replot` fails | Saved `npz` data is missing or incomplete. | Run the corresponding tool once without `--replot`. |
| Results are not in git | `results/` is intentionally ignored. | Regenerate them locally; source and documentation are tracked. |

## Stopping and cleanup

Stop a launch with `Ctrl+C`. If a process survived an interrupted run:

```bash
pkill -9 -f lib/navigator_sim
pkill -9 -f lib/navigator_slam
pkill -9 -f /opt/ros/jazzy/lib/robot_state_publisher
pkill -9 -f /opt/ros/jazzy/lib/tf2_ros/static_transform_publisher
```

Remove build artefacts only when necessary:

```bash
rm -rf build install log
colcon build --symlink-install
```

## Logs and diagnostics

- Launch output is printed to the terminal; exceptions usually appear within
  the first seconds.
- `ros2 node list` shows which nodes actually started.
- `ros2 topic info <topic> -v` shows publishers, subscribers and QoS.
- `ros2 topic hz <topic>` and `ros2 topic echo --once <topic>` confirm data
  flow.
- `ros2 run tf2_ros tf2_echo map base_footprint` checks the transform chain.
- `ros2 doctor --report` prints a detailed environment report.

## Related documentation

- [Architecture](architecture.md) — nodes, topics and frames.
- [Configuration](configuration.md) — parameters and defaults.
- [Verification](verification.md) — expected rates and outputs.
- [WSL setup](wsl-setup.md) — installation from scratch.
