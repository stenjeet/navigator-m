# ROS API

[English](../en/ros-api.md) | **Русский**

Этот документ описывает публичный runtime-интерфейс workspace: узлы, топики,
типы сообщений, системы координат, параметры и аргументы launch-файлов.
Документ проверяется по исходному коду скриптом `tools/check_docs.py`.

## Узлы

| Узел | Имя по умолчанию | Пакет |
|---|---|---|
| Истинное движение | `motion_node` | `navigator_sim` |
| Маркеры полигона | `polygon_markers` | `navigator_sim` |
| Модель СШП | `uwb_model_node` | `navigator_sim` |
| Модель лидара | `lidar_model_node` | `navigator_sim` |
| EKF-локализатор | `ekf_node` | `navigator_localization` |
| Картограф занятости | `occupancy_grid_ekf`, `occupancy_grid_gt` | `navigator_slam` |
| Детектор ориентиров | `landmark_node` | `navigator_slam` |
| EKF-SLAM | `ekf_slam_node` | `navigator_slam` |

Launch-файлы также используют стандартные вспомогательные узлы ROS 2
(`robot_state_publisher`, `joint_state_publisher`,
`static_transform_publisher`).

## Топики

Если не указано иное, издатели и подписчики используют стандартный QoS-профиль
ROS 2 (reliable, volatile, depth 10). `/robot_description` и `/tf_static`
публикуются соответствующими стандартными узлами как latched.

| Топик | Тип | Издатель | Подписчики |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | `motion_node` | `ekf_node`, `ekf_slam_node` |
| `/ground_truth/odom` | `nav_msgs/Odometry` | `motion_node` | `ekf_node`, `ekf_slam_node` |
| `/ground_truth/path` | `nav_msgs/Path` | `motion_node` | RViz |
| `/joint_states` | `sensor_msgs/JointState` | `motion_node`, `joint_state_publisher` | `robot_state_publisher` |
| `/scan_ideal` | `sensor_msgs/LaserScan` | `lidar_model_node` | RViz, инструменты |
| `/scan_noisy` | `sensor_msgs/LaserScan` | `lidar_model_node` | `occupancy_grid_node`, `landmark_node`, RViz, инструменты |
| `/uwb/ideal_ranges` | `std_msgs/Float32MultiArray` | `uwb_model_node` | инструменты |
| `/uwb/noisy_ranges` | `std_msgs/Float32MultiArray` | `uwb_model_node` | `ekf_node`, `ekf_slam_node` |
| `/uwb/anchors` | `visualization_msgs/MarkerArray` | `uwb_model_node` | RViz |
| `/polygon_markers` | `visualization_msgs/MarkerArray` | `polygon_markers` | RViz |
| `/estimate/odom` | `nav_msgs/Odometry` | `ekf_node` | `occupancy_grid_node`, `landmark_node`, инструменты, RViz |
| `/estimate/path` | `nav_msgs/Path` | `ekf_node` | RViz |
| `/estimate/error` | `geometry_msgs/Vector3Stamped` | `ekf_node` | инструменты |
| `/map` | `nav_msgs/OccupancyGrid` | `occupancy_grid_node` | — |
| `/map/estimate` | `nav_msgs/OccupancyGrid` | `occupancy_grid_ekf` | RViz, инструменты |
| `/map/ground_truth` | `nav_msgs/OccupancyGrid` | `occupancy_grid_gt` | RViz, инструменты |
| `/landmarks/observations` | `navigator_interfaces/LandmarkObservationArray` | `landmark_node` | `ekf_slam_node` |
| `/landmarks/map` | `navigator_interfaces/LandmarkMap` | `landmark_node` | RViz, инструменты |
| `/landmarks/markers` | `visualization_msgs/MarkerArray` | `landmark_node` | RViz |
| `/slam/odom` | `nav_msgs/Odometry` | `ekf_slam_node` | RViz, инструменты |
| `/slam/path` | `nav_msgs/Path` | `ekf_slam_node` | RViz |
| `/slam/landmarks` | `navigator_interfaces/LandmarkMap` | `ekf_slam_node` | RViz, инструменты |
| `/slam/markers` | `visualization_msgs/MarkerArray` | `ekf_slam_node` | RViz |
| `/slam/error` | `geometry_msgs/Vector3Stamped` | `ekf_slam_node` | инструменты |
| `/robot_description` | `std_msgs/String` | `robot_state_publisher` | RViz, `joint_state_publisher` |
| `/tf` | `tf2_msgs/TFMessage` | `motion_node`, `robot_state_publisher` | все потребители TF |
| `/tf_static` | `tf2_msgs/TFMessage` | `static_transform_publisher`, `robot_state_publisher` | все потребители TF |

`/map` — значение параметра `map_topic` картографа по умолчанию. Launch-файл
переопределяет его на `/map/estimate` или `/map/ground_truth`.

## Сообщения

### `navigator_interfaces/LandmarkObservation`

| Поле | Тип | Единица | Назначение |
|---|---|---|---|
| `range` | `float64` | м | Расстояние от начала координат робота до центра ориентира. |
| `bearing` | `float64` | рад | Угол относительно курса робота, в `(-pi, pi]`. |
| `radius` | `float64` | м | Радиус аппроксимирующей окружности ориентира. |
| `range_variance` | `float64` | м^2 | Дисперсия дальности. |
| `bearing_variance` | `float64` | рад^2 | Дисперсия азимута. |

### `navigator_interfaces/LandmarkObservationArray`

| Поле | Тип | Назначение |
|---|---|---|
| `header` | `std_msgs/Header` | Штамп — время скана; система координат — `base_footprint`. |
| `observations` | `navigator_interfaces/LandmarkObservation[]` | Наблюдения из одного скана. |

### `navigator_interfaces/Landmark`

| Поле | Тип | Единица | Назначение |
|---|---|---|---|
| `id` | `int32` | — | Стабильный id ориентира, назначенный трекером. |
| `x` | `float64` | м | Координата `x` ориентира в `map`. |
| `y` | `float64` | м | Координата `y` ориентира в `map`. |
| `covariance` | `float64[4]` | м^2 | Построчная ковариация положения 2x2. |

### `navigator_interfaces/LandmarkMap`

| Поле | Тип | Назначение |
|---|---|---|
| `header` | `std_msgs/Header` | Система координат — `map`. |
| `landmarks` | `navigator_interfaces/Landmark[]` | Известные ориентиры. |

## Системы координат

| Система | Родитель | Публикует |
|---|---|---|
| `map` | — | Фиксированная мировая система. |
| `odom` | `map` | `static_transform_publisher` (identity). |
| `base_footprint` | `odom` | `motion_node` (истинная поза). |
| `base_link` | `base_footprint` | `robot_state_publisher`. |
| `front_panel_link` | `base_link` | `robot_state_publisher`. |
| `left_wheel_link` | `base_link` | `robot_state_publisher`. |
| `right_wheel_link` | `base_link` | `robot_state_publisher`. |
| `front_caster_link` | `base_link` | `robot_state_publisher`. |
| `rear_caster_link` | `base_link` | `robot_state_publisher`. |
| `lidar_link` | `base_link` | `robot_state_publisher`. |
| `uwb_tag_link` | `base_link` | `robot_state_publisher`. |
| `computer_link` | `base_link` | `robot_state_publisher`. |

`ekf_node` и `ekf_slam_node` публикуют позы в топики, но не транслируют TF.
Симулятор держит `map -> odom` фиксированной, поэтому системы `map` и `odom`
совпадают.

## Параметры

Все runtime-параметры с значениями по умолчанию описаны в
[Конфигурации](configuration.md). Пространства имён параметров:

| Узел | Файл параметров |
|---|---|
| `motion_node` | `navigator_sim/config/motion.yaml` |
| `uwb_model_node`, `lidar_model_node` | `navigator_sim/config/sensors.yaml` |
| `ekf_node` | `navigator_localization/config/ekf.yaml` |
| `occupancy_grid_node` | `navigator_slam/config/occupancy.yaml` |
| `landmark_node` | `navigator_slam/config/landmarks.yaml` |
| `ekf_slam_node` | `navigator_slam/config/ekf_slam.yaml` |

## Аргументы launch-файлов

| Launch-файл | Аргумент | Значение по умолчанию |
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

## Сервисы и действия

Workspace не предоставляет ROS-сервисов и действий. Всё взаимодействие идёт
через топики и TF.

## Проверка

Документ API и языковые пары документации проверяются командой:

```bash
python3 tools/check_docs.py
```

Скрипт проверяет имена топиков, параметров, аргументов launch-файлов, файлы и
поля сообщений, а также структурное соответствие каждой англо-русской пары.

## Связанная документация

- [Архитектура](architecture.md) — поток данных и состав launch-файлов.
- [Конфигурация](configuration.md) — значения параметров по умолчанию.
- [Проверка](verification.md) — runtime-проверки.
