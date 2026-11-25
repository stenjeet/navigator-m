# Running the Project on Windows 11 + WSL 2 (Ubuntu 24.04, ROS 2 Jazzy)

**English** | [Русский](../ru/wsl-setup.md)

Step-by-step guide: from a clean Windows install to a working simulation.
The project is the `navigator-m` folder (with six packages inside `src/`:
`navigator_description`, `navigator_sim`, `navigator_bringup`,
`navigator_localization`, `navigator_slam`, `navigator_interfaces`). Launch
commands, parameters and topics: [`usage.md`](usage.md). Tests and
runtime checks: [`verification.md`](verification.md).

> Version matching: **Ubuntu 24.04 → ROS 2 Jazzy**. ROS 2 Humble is only
> available on Ubuntu 22.04, so it is not used here.

---

## 1. Install WSL 2 and Ubuntu 24.04

In **PowerShell as Administrator**:

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
```

After rebooting, set a username and password the first time Ubuntu starts.
Check the WSL version:

```powershell
wsl -l -v
```

It should show `VERSION 2`. If it shows `1`:

```powershell
wsl --set-version Ubuntu-24.04 2
```

All subsequent commands are run **inside Ubuntu** (the "Ubuntu-24.04" terminal).

---

## 2. Install ROS 2 Jazzy

```bash
sudo apt update && sudo apt install -y locales software-properties-common curl
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

sudo add-apt-repository universe -y
sudo apt update

# official ROS repository
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo $VERSION_CODENAME)_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

sudo apt update && sudo apt upgrade -y

# ROS 2 Jazzy Desktop (includes RViz2) + build tools.
# joint_state_publisher is needed by display.launch.py (static robot view).
sudo apt install -y ros-jazzy-desktop ros-dev-tools ros-jazzy-joint-state-publisher

echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
source ~/.bashrc
```

Check: `printenv ROS_DISTRO` → `jazzy`.

Required for EKF localization:

```bash
sudo apt install -y python3-numpy python3-yaml
```

Optional (figures from `run_visualize.sh` and running tests):

```bash
sudo apt install -y python3-matplotlib python3-pytest
```

---

## 3. Copy the Project to the Linux File System

Do not build in `/mnt/c/...`: it is slow and file permissions break. The project
must live in the WSL home directory, for example `~/navigator-m`.

If the folder is on Windows, for example `C:\Users\<Name>\Downloads\navigator-m`:

```bash
cp -r "/mnt/c/Users/<Name>/Downloads/navigator-m" ~/navigator-m
cd ~/navigator-m
ls        # README.md  LICENSE  run.sh  src/  docs/
```

If you downloaded a zip archive:

```bash
cd ~
unzip "/mnt/c/Users/<Name>/Downloads/navigator-m.zip"
```

---

## 4. Build

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Expected: `Summary: 6 packages finished` (`navigator_description`, `navigator_sim`,
`navigator_bringup`, `navigator_localization`, `navigator_slam`,
`navigator_interfaces`).

---

## 5. Run

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# with RViz (Windows 11 — WSLg, the window opens automatically):
ros2 launch navigator_bringup simulation.launch.py

# without graphics (works on any configuration):
ros2 launch navigator_bringup simulation.launch.py use_rviz:=false
```

Shortcut — a script (build + run):

```bash
./run.sh                     # RViz
./run.sh use_rviz:=false     # headless
```

Static view of the model and the map:

```bash
ros2 launch navigator_bringup display.launch.py
```

Simulation + EKF localization:

```bash
ros2 launch navigator_bringup localization.launch.py
# equivalent:
ros2 launch navigator_bringup simulation.launch.py use_localization:=true
```

Occupancy grid from the estimated pose (EKF starts automatically):

```bash
ros2 launch navigator_bringup mapping.launch.py
# map from the ground-truth pose (no EKF):
ros2 launch navigator_bringup mapping.launch.py pose_source:=ground_truth
# both maps at once — for comparison:
ros2 launch navigator_bringup mapping.launch.py pose_source:=both
```

Landmark extraction (pose from EKF) and EKF-SLAM:

```bash
ros2 launch navigator_bringup landmarks.launch.py     # landmarks + tracker map (EKF pose)
ros2 launch navigator_bringup landmarks.launch.py pose_topic:=/ground_truth/odom  # detector only
ros2 launch navigator_bringup slam.launch.py          # joint EKF-SLAM
```

To stop — `Ctrl+C`.

---

## 6. Checks (Second Ubuntu Terminal)

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash && source install/setup.bash

ros2 pkg list | grep navigator             # 6 packages
ros2 node list                              # 6 without EKF; 7 with EKF; 8 with landmark_node; 8 with SLAM; 9 with two mappers (+1 with RViz)
ros2 topic list                             # list of topics
ros2 topic hz /scan_ideal                   # ~10 Hz
ros2 topic hz /uwb/noisy_ranges             # ~10 Hz
ros2 topic echo --once /uwb/noisy_ranges    # 4 ranges (NaN = dropout)
ros2 topic echo --once /ground_truth/odom   # ground-truth pose
ros2 run tf2_ros tf2_echo map base_footprint
ros2 topic hz /estimate/odom                # ~20 Hz (if EKF is enabled)
ros2 topic echo --once /estimate/error      # estimation error
ros2 topic hz /map/estimate                 # ~1 Hz (if the mapper is running)
ros2 topic echo --once /map/estimate         # OccupancyGrid: -1/0/100
ros2 topic hz /landmarks/observations        # ~10 Hz
ros2 topic hz /slam/odom                     # ~20 Hz
ros2 topic echo --once /slam/landmarks       # EKF-SLAM landmark map
ros2 topic echo --once /slam/error           # SLAM error vs ground truth
```

Expected: 6 nodes without EKF, 7 with `use_localization:=true`, 8 with
`landmark_node`, 8 with SLAM (`slam.launch.py`), and 9 with `pose_source:=both`
(one more node with RViz); all topics from `README.md`, frequencies ~10 Hz,
TF moving along a 4 × 4 m square at 0.35 m/s; `/estimate/odom` at ~20 Hz.

### EKF Checks

Unit tests (no simulation):

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash && source install/setup.bash
PYTHONPATH=src/navigator_localization:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_localization/test -v
# or via colcon:
colcon test --packages-select navigator_localization
colcon test-result --verbose
```

Run with EKF and check (second terminal):

```bash
ros2 launch navigator_bringup localization.launch.py use_rviz:=false
ros2 topic hz /estimate/odom
ros2 topic echo --once /estimate/odom
ros2 topic echo --once /estimate/error
```

`ekf_node` prints `RMSE x=... y=... yaw=...` once per second in the log.
With noisy UWB the position error is a few centimeters. Heading from a single
tag is not observable in static conditions, so it is refined while turning.

Error plots and the final RMSE in one command:

```bash
cd ~/navigator-m
./run_localization_metrics.sh          # 62 s
./run_localization_metrics.sh 90       # 90 s
```

Results: `results/result_localization_trajectory.png` (ground truth vs estimate)
and `results/result_localization_error.png` (`x`, `y`, `yaw` errors); RMSE is
printed to the console.

### Occupancy Grid Checks

Unit tests (no ROS):

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash && source install/setup.bash
PYTHONPATH=src/navigator_slam:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_slam/test -v
colcon test --packages-select navigator_slam
```

Run and check (second terminal):

```bash
ros2 launch navigator_bringup mapping.launch.py use_rviz:=false pose_source:=both
ros2 topic hz /map/estimate            # ~1 Hz
ros2 topic echo --once /map/estimate   # width/height 180, resolution 0.05, data from -1/0/100
```

`occupancy_grid_ekf` prints the number of scans and the count of
occupied/free/unknown cells once per second in the log. Compare maps with a
single command:

```bash
cd ~/navigator-m
./run_map_compare.sh          # 62 s
./run_map_compare.sh 90       # 90 s
```

The result is `results/result_map_compare.png` (map from the ground-truth pose,
map from the estimate, and a difference map) plus the IoU of occupied cells and
the fraction of matching cells in the console. To redraw:
`python3 tools/map_compare.py --replot`.

### Landmark and EKF-SLAM Checks

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash && source install/setup.bash
colcon test --packages-select navigator_slam && colcon test-result --verbose   # 177 tests
```

Running: `landmarks.launch.py` starts the simulation + EKF + `landmark_node`
(`/landmarks/observations`, `/landmarks/map`, `/landmarks/markers`);
`slam.launch.py` starts the simulation without EKF, `landmark_node` with an
empty `pose_topic` (observations only) and `ekf_slam_node` (`/slam/odom`,
`/slam/path`, `/slam/landmarks`, `/slam/markers`, `/slam/error`). In the log
`ekf_slam_node` prints the pose RMSE relative to ground truth once per second.

Checks:

```bash
ros2 topic echo --once /landmarks/observations   # 1-4 landmarks, base_footprint
ros2 topic echo --once /slam/landmarks           # 4 landmarks with id and covariance
ros2 topic echo --once /slam/error               # x, y, yaw vs /ground_truth/odom
```

### Performance Analysis Checks

```bash
cd ~/navigator-m
./run_analysis.sh --quick      # 3 scenarios of 30 s (~3 min)
./run_analysis.sh              # 10 scenarios of 62 s (~13 min)
```

Results: `results/analysis/summary.md` (table + conclusions),
`results/analysis/summary.csv`, `results/analysis_rmse.png`,
`results/analysis_maps.png`. To redraw:
`python3 tools/analysis.py --replot`.

---

## 7. Generating Figures (Optional)

The script runs a headless simulation, records ~62 s of data and renders PNGs
into `results/`:

```bash
cd ~/navigator-m
./run_visualize.sh          # 62 s
./run_visualize.sh 90       # 90 s
```

Redraw from saved data (no simulation):

```bash
source /opt/ros/jazzy/setup.bash && source install/setup.bash
python3 tools/visualize.py --replot
```

---

## 8. Common Problems

| Symptom | Cause / fix |
|---|---|
| `ros2: command not found` | `source /opt/ros/jazzy/setup.bash` and `source install/setup.bash` are not sourced |
| `ros2 topic echo`: "The message type `navigator_interfaces/msg/...` is invalid" | only the system ROS is sourced in the terminal: run `source install/setup.bash` (otherwise the Python modules of the project messages are not visible), and check the topic while the launch is running |
| `E: Unable to locate package ros-jazzy-desktop` | `apt update` was not run after adding the repository, or Ubuntu is not 24.04 |
| `package 'joint_state_publisher' not found` with `display.launch.py` | the package is not part of the minimal desktop: `sudo apt install -y ros-jazzy-joint-state-publisher` |
| Slow build / permission errors | the project is in `/mnt/c` — copy it to `~` (section 3) |
| `colcon build` behaves strangely | run it from the `~/navigator-m` root, not from `src` |
| RViz does not open (Windows 10) | no WSLg: install VcXsrv/Xming and set `export DISPLAY=$(ip route show default \| awk '{print $3}'):0.0` |
| RViz crashes with an OpenGL error | `sudo apt install -y mesa-utils libgl1-mesa-dri` and restart WSL (`wsl --shutdown`) |
| Processes remain after `Ctrl+C` | `pkill -9 -f lib/navigator_sim; pkill -9 -f lib/navigator_slam` |
| `plot_data.npz`/PNGs were not created | `python3-numpy` and `python3-matplotlib` are not installed — see section 2 |
| `ModuleNotFoundError: No module named 'numpy'` | `python3-numpy` is not installed — `sudo apt install -y python3-numpy` |
| `Package 'navigator_localization' not found` | the workspace has not been rebuilt — `colcon build --symlink-install`, then `source install/setup.bash` |
| EKF does not start | `use_localization:=false` is the default; use `localization.launch.py` or `use_localization:=true` |
| `/map/estimate` is empty or missing | the mapper is not running or the pose was not found: `mapping.launch.py` (`pose_source:=estimate`/`both`) and a non-empty `/estimate/odom` |
| "no map on ..." in `map_compare.py` | `mapping.launch.py` was started without `pose_source:=both` |
| `/landmarks/observations` is silent | `landmark_node` is not running (`landmarks.launch.py` / `slam.launch.py`) or there are no landmarks in view |
| `/slam/odom` is missing | `slam.launch.py` is not running; SLAM does not need EKF localization |
| `analysis.py` fails at scenario start | EKF has not published `/estimate/error` yet — increase `--startup-timeout` |
| "sensor parameters were not applied" | check the sections in `sensors.yaml`: the section name must match the node name (`uwb_model_node`, `lidar_model_node`) |
| `uwb_model_node` crashes with `ParameterUninitializedException: anchors` | the YAML has `anchors: []`; ROS cannot infer the type of an empty array — remove the key (polygon anchors will be used) or specify all `x, y, z` triples |
