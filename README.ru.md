# Navigator-M

[English](README.md) | **Русский**

![ROS 2 Jazzy](https://img.shields.io/badge/ROS%202-Jazzy-22314E)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

ROS 2 workspace для симуляции, локализации и SLAM автономного
дифференциального робота «Навигатор-М». Проект объединяет детерминированный
симулятор полигона, модели UWB- и лидарных измерений, EKF-локализацию,
построение сетки занятости, детектор ориентиров и совместный EKF-SLAM.

## Возможности

- Симуляция полигона 8 × 8 м с препятствиями, UWB-якорями и ориентирами.
- Истинное движение робота по квадратной траектории и одометрия.
- Модели UWB-дальностей и лидарных сканов с шумом, смещением и пропусками.
- EKF-локализация по дальностям до UWB-якорей.
- Сетка занятости в log-odds по лидарным сканам.
- Детектор ориентиров, ассоциация наблюдений и подтверждение кандидатов.
- Совместный EKF-SLAM: поза робота и карта ориентиров в одном фильтре.
- Инструменты для метрик локализации, сравнения карт и сценарного анализа.
- 197 юнит-тестов, которые запускаются без установленного ROS.

## Требования

- Ubuntu 24.04 или Windows + WSL 2 с Ubuntu 24.04.
- ROS 2 Jazzy: `ros-jazzy-desktop`, `ros-dev-tools`,
  `ros-jazzy-joint-state-publisher`.
- Для построения графиков: `python3-numpy`, `python3-matplotlib`.

Пошаговая установка WSL 2, Ubuntu и ROS 2 описана в
[`docs/ru/wsl-setup.md`](docs/ru/wsl-setup.md).

## Быстрый старт

```bash
git clone <repository-url> navigator-m
cd navigator-m

source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash

./run.sh
```

`./run.sh` собирает workspace и запускает полную симуляцию с RViz. Для
headless-запуска:

```bash
./run.sh use_rviz:=false
```

## Запуск

| Команда | Что запускает |
|---|---|
| `./run.sh` | Полная симуляция: движение, UWB, лидар, карта, RViz. |
| `./run.sh use_rviz:=false` | То же без графического интерфейса. |
| `ros2 launch navigator_bringup display.launch.py` | Статичный показ модели и полигона. |
| `ros2 launch navigator_bringup localization.launch.py` | Симуляция и EKF-локализация. |
| `ros2 launch navigator_bringup mapping.launch.py` | Сетка занятости по оценке EKF. |
| `ros2 launch navigator_bringup mapping.launch.py pose_source:=both` | Две карты: по оценке и по истинной позе. |
| `ros2 launch navigator_bringup landmarks.launch.py` | Детектор и карта ориентиров. |
| `ros2 launch navigator_bringup slam.launch.py` | Совместный EKF-SLAM. |

У launch-файлов есть аргумент `use_rviz` (по умолчанию `true`).
`simulation.launch.py` также принимает `use_localization`, `sensors_params` и
`ekf_params`; `mapping.launch.py` — `pose_source` (`estimate`, `ground_truth`
или `both`).

## Пакеты

| Пакет | Назначение |
|---|---|
| `navigator_description` | URDF робота и конфигурация RViz. |
| `navigator_sim` | Геометрия полигона, истинное движение, модели UWB и лидара. |
| `navigator_localization` | EKF-локализация по UWB-дальностям. |
| `navigator_slam` | Сетка занятости, ориентиры и совместный EKF-SLAM. |
| `navigator_interfaces` | Сообщения для ориентиров и карт. |
| `navigator_bringup` | Launch-файлы для сборки всего стека. |
| `tools/` | Метрики, сравнение карт, графики и сценарный анализ. |

Пакеты разделены по ролям: `navigator_description` можно переиспользовать с
реальным роботом, `navigator_sim` заменяется драйверами датчиков, а
`navigator_bringup` собирает систему целиком.

## Основные топики

| Топик | Тип | Назначение |
|---|---|---|
| `/ground_truth/odom` | `nav_msgs/Odometry` | Истинная поза робота. |
| `/scan_noisy` | `sensor_msgs/LaserScan` | Лидарный скан с шумом и пропусками. |
| `/uwb/noisy_ranges` | `std_msgs/Float32MultiArray` | UWB-дальности, `NaN` — пропуск. |
| `/estimate/odom` | `nav_msgs/Odometry` | Оценка позы EKF. |
| `/estimate/error` | `geometry_msgs/Vector3Stamped` | Ошибка EKF относительно истины. |
| `/map/estimate` | `nav_msgs/OccupancyGrid` | Карта по оценке EKF. |
| `/map/ground_truth` | `nav_msgs/OccupancyGrid` | Эталонная карта по истинной позе. |
| `/landmarks/observations` | `navigator_interfaces/LandmarkObservationArray` | Ориентиры в системе робота. |
| `/landmarks/map` | `navigator_interfaces/LandmarkMap` | Карта ориентиров трекера. |
| `/slam/odom` | `nav_msgs/Odometry` | Поза из EKF-SLAM. |
| `/slam/landmarks` | `navigator_interfaces/LandmarkMap` | Карта ориентиров EKF-SLAM. |
| `/slam/error` | `geometry_msgs/Vector3Stamped` | Ошибка EKF-SLAM относительно истины. |

Полный справочник по узлам, топикам и параметрам — в
[`docs/ru/ros-api.md`](docs/ru/ros-api.md).

## Тесты

Быстрые тесты без ROS:

```bash
PYTHONPATH=src/navigator_slam:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_slam/test

PYTHONPATH=src/navigator_localization:src/navigator_sim \
  python3 -m unittest discover -s src/navigator_localization/test

PYTHONPATH=src/navigator_sim:src/navigator_description \
  python3 -m unittest discover -s src/navigator_sim/test
```

Проверка через `colcon`:

```bash
colcon test
colcon test-result --verbose
```

## Инструменты

| Команда | Назначение |
|---|---|
| `./run_visualize.sh [секунды]` | Headless-прогон и рисунки полигона, скана и UWB. |
| `./run_localization_metrics.sh [секунды]` | Ошибки EKF и графики траектории. |
| `./run_map_compare.sh [секунды]` | Сравнение карт по истинной и оценённой позе. |
| `./run_analysis.sh [--quick]` | Сценарный анализ точности локализации и карт. |
| `python3 tools/check_docs.py` | Проверка ROS API и соответствия EN/RU документации. |

Все результаты записываются в `results/`, который исключён из git. Повторная
отрисовка сохранённых данных доступна через `--replot` у соответствующего
инструмента.

## Документация

- [`docs/README.md`](docs/README.md) — выбор языка документации.
- [`docs/ru/README.md`](docs/ru/README.md) — индекс русской документации.
- [`docs/ru/usage.md`](docs/ru/usage.md) — команды запуска, скрипты и ручной
  запуск.
- [`docs/ru/ros-api.md`](docs/ru/ros-api.md) — публичный ROS API: узлы, топики,
  сообщения, системы координат, параметры и аргументы launch-файлов.
- [`docs/ru/architecture.md`](docs/ru/architecture.md) — пакеты, поток данных,
  системы координат и топики.
- [`docs/ru/configuration.md`](docs/ru/configuration.md) — параметры YAML и
  аргументы launch-файлов.
- [`docs/ru/algorithms.md`](docs/ru/algorithms.md) — EKF, сетка занятости,
  детектор ориентиров и EKF-SLAM.
- [`docs/ru/verification.md`](docs/ru/verification.md) — тесты, runtime-проверки,
  ожидаемые результаты и известные ограничения.
- [`docs/ru/troubleshooting.md`](docs/ru/troubleshooting.md) — типичные
  проблемы при запуске.
- [`docs/ru/wsl-setup.md`](docs/ru/wsl-setup.md) — установка Windows + WSL 2 + ROS 2
  Jazzy.
- [`LICENSE`](LICENSE) — лицензия MIT.

## Лицензия

Проект распространяется по лицензии MIT. Подробности — в [`LICENSE`](LICENSE).
