# Подробное руководство

[English](../en/usage.md) | **Русский**

Расширенное руководство по запуску, топикам, параметрам и алгоритмам.
Краткая стартовая страница — в [README](../../README.ru.md).

Рабочее пространство ROS 2 проекта **navigator**: модель робота, карта полигона,
истинная квадратная траектория, модели СШП-дальностей и лидарных сканов,
EKF-локализация по СШП, сетка занятости, выделение ориентиров и EKF-SLAM.

Основная среда — **Ubuntu 24.04 с ROS 2 Jazzy**; Windows 11 через WSL 2 также
поддерживается. Пошаговая установка с нуля:
[`wsl-setup.md`](wsl-setup.md). Код использует только `rclpy`,
стандартные сообщения и `launch`, поэтому собирается и на ROS 2 Humble
(Ubuntu 22.04).

## Быстрый старт

```bash
cd ~/navigator-m                   # проект должен лежать в файловой системе Linux, не в /mnt/c
./run.sh use_rviz:=false            # сборка + headless-симуляция; Ctrl+C для остановки
./run.sh                            # то же, но с окном RViz (Windows 11 — через WSLg)
```

Дальше — проверка во втором терминале (раздел [Проверка](#проверка)) или снятие рисунков: `./run_visualize.sh`.

## Структура

Workspace содержит шесть ROS 2 пакетов в `src/`, офлайн-инструменты в `tools/`
и документацию в `docs/`. Ответственность пакетов, поток данных, системы
координат и полный список топиков описаны в [Архитектуре](architecture.md).

## Требования

- Ubuntu 24.04 + ROS 2 Jazzy: `ros-jazzy-desktop` (включает RViz2), `ros-dev-tools` (colcon), `ros-jazzy-joint-state-publisher` (для `display.launch.py`).
- Для рисунков: `python3-numpy`, `python3-matplotlib`.

## Сборка (один раз)

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Ожидаемо: `Summary: 6 packages finished` (`navigator_description`, `navigator_sim`,
`navigator_bringup`, `navigator_localization`, `navigator_slam`,
`navigator_interfaces`).

## Скрипты

| Команда | Что делает |
|---|---|
| `./run.sh [аргументы launch]` | `colcon build --symlink-install`, `source install/setup.bash`, `ros2 launch navigator_bringup simulation.launch.py`. Аргументы пробрасываются в launch: `./run.sh use_rviz:=false`. Собирает при каждом запуске (~пара секунд), чтобы не стартовать устаревший код. |
| `./run_visualize.sh [секунды]` | Запускает `tools/visualize.py` в фоне, поднимает headless-симуляцию, пишет данные (62 с по умолчанию, можно `./run_visualize.sh 90`), рендерит PNG в `results/`, затем гасит симуляцию. **Требует уже собранный `install/`** — после правок кода сначала `./run.sh` или `colcon build`. |
| `python3 tools/visualize.py --replot` | Перерисовывает графики из сохранённого `results/plot_data.npz` без запуска симуляции. Дополнительно: `--duration N`, `--out DIR`. |
| `./run_localization_metrics.sh [секунды]` | headless-прогон с EKF, запись `/ground_truth/odom` и `/estimate/odom` (62 с по умолчанию), PNG и RMSE в `results/`. |
| `python3 tools/localization_metrics.py --replot` | Перерисовывает метрики из `results/localization_data.npz`. |
| `./run_map_compare.sh [секунды]` | headless-прогон с двумя картографами (истинная поза и оценка EKF), сравнение карт, PNG, расстояние и IoU в `results/`. |
| `python3 tools/map_compare.py --replot` | Перерисовывает сравнение карт из `results/map_compare_data.npz`. |
| `./run_analysis.sh [секунды] [--quick]` | Последовательно прогоняет сценарии (σ СШП, пропуски, окно без СШП, раскладки якорей), пишет таблицу и графики в `results/`. |
| `python3 tools/analysis.py --replot` | Перерисовывает таблицу и графики анализа из `results/analysis/analysis_data.npz`. |

Все shell-скрипты берут дистрибутив ROS из `/opt/ros/jazzy/setup.bash`; другой путь можно
задать переменной, например `ROS_SETUP=/opt/ros/humble/setup.bash ./run.sh`.

## Запуск вручную

```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# движение + СШП + лидар + карта + RViz
ros2 launch navigator_bringup simulation.launch.py

# без графики
ros2 launch navigator_bringup simulation.launch.py use_rviz:=false

# статичный показ модели и карты (без движения);
# use_rviz:=false — только headless smoke-test без окна
ros2 launch navigator_bringup display.launch.py

# симуляция + EKF-локализация
ros2 launch navigator_bringup localization.launch.py
# эквивалент:
ros2 launch navigator_bringup simulation.launch.py use_localization:=true

# сетка занятости по оценке EKF (EKF стартует автоматически)
ros2 launch navigator_bringup mapping.launch.py
# карта по истинной позе / обе карты сразу (для сравнения)
ros2 launch navigator_bringup mapping.launch.py pose_source:=ground_truth
ros2 launch navigator_bringup mapping.launch.py pose_source:=both

# выделение ориентиров и ассоциация (поза — EKF)
ros2 launch navigator_bringup landmarks.launch.py
# EKF-SLAM (совместная оценка позы и карты ориентиров)
ros2 launch navigator_bringup slam.launch.py

# детектор и ассоциация с истинной позой
ros2 launch navigator_bringup landmarks.launch.py pose_topic:=/ground_truth/odom
```

У всех launch-файлов есть аргумент `use_rviz` (по умолчанию `true`);
`simulation.launch.py` принимает `use_localization`, `sensors_params` и
`ekf_params` (сценарные YAML анализа), `mapping.launch.py` — `pose_source`
(`estimate` по умолчанию, `ground_truth`, `both`) и пробрасывает
`sensors_params`/`ekf_params`.

## Узлы и топики

Полный справочник по узлам, топикам, системам координат и составу launch-файлов
находится в [Архитектуре](architecture.md). Основные runtime-топики также
перечислены в [README](../../README.ru.md).

## Проверка

Матрица тестов, runtime-проверки, ожидаемые результаты и известные ограничения
описаны в [Руководстве по проверке](verification.md).

## Обработка данных

- **EKF-локализация** превращает `/cmd_vel` и `/uwb/noisy_ranges` в
  `/estimate/odom`.
- **Сетка занятости** строит `/map/estimate` или `/map/ground_truth` по
  `/scan_noisy` и позе.
- **Детектор ориентиров** публикует `/landmarks/observations` и
  `/landmarks/map` по сканам и позе.
- **EKF-SLAM** объединяет `/cmd_vel`, дальности СШП и наблюдения ориентиров в
  `/slam/odom` и `/slam/landmarks`.

Модели, уравнения и обоснование параметров — в [Алгоритмах](algorithms.md).

## Анализ эффективности

`tools/analysis.py` последовательно прогоняет сценарии, варьируя параметры через
сгенерированные YAML (`sensors_params`/`ekf_params`), и агрегирует метрики:

| Сценарий | Что меняется |
|---|---|
| `baseline` | номинальные `sensors.yaml` и `ekf.yaml` |
| `uwb_sigma_0.02/0.10/0.20` | σ СШП в модели **и** в фильтре |
| `uwb_mismatch_r_low` | модель 0.10 м, фильтр 0.05 м (оптимистичный R) |
| `dropout_0.10/0.25` | вероятность пропуска СШП |
| `outage_20_40` | все дальности `NaN` с 20-й по 40-ю секунду |
| `anchors_wide` / `anchors_compact` | углы полигона / якоря у старта |

Метрики: RMSE и максимум ошибки позы (`/estimate/error`), IoU занятых ячеек и
среднее расстояние между картами `/map/estimate` и `/map/ground_truth`.
Точность EKF-SLAM проверяется отдельным запуском `slam.launch.py`
(`/slam/error` и RMSE в логе `ekf_slam_node`), в сценарную таблицу она не
входит. Результаты:
`results/analysis/summary.md` (таблица + автоматические выводы),
`results/analysis/summary.csv`, `results/analysis_rmse.png`,
`results/analysis_maps.png`.

```bash
./run_analysis.sh --quick      # baseline + σ 0.10 + dropout 0.25, по 30 с (~3 мин)
./run_analysis.sh              # полная таблица, по 62 с (~13 мин)
python3 tools/analysis.py --replot   # таблица и графики без запуска симуляции
```

Первые 3 с после первого `/estimate/error` отбрасываются как прогрев
(`--warmup`, по умолчанию 3 с): EKF стартует с фиксированной начальной позой,
пока робот уже движется, и этот переходный процесс иначе даёт большой
`max |e|`, не относящийся к установившейся точности.

## Остановка

`Ctrl+C` в терминале запуска. Если после аварийного прерывания остались процессы:

```bash
pkill -9 -f lib/navigator_sim
pkill -9 -f lib/navigator_slam
pkill -9 -f /opt/ros/jazzy/lib/robot_state_publisher
pkill -9 -f /opt/ros/jazzy/lib/tf2_ros/static_transform_publisher
```

## Параметры

Все YAML-файлы, значения параметров по умолчанию и аргументы launch-файлов
перечислены в [Конфигурации](configuration.md).

## Генерация рисунков

```bash
./run_visualize.sh        # headless-прогон ~62 с, PNG в results/
./run_visualize.sh 90     # более длинная запись
```

| Файл | Что показывает |
|------|----------------|
| `results/result_map.png` | вид сверху: полигон, истинная траектория, накопленная карта лидара |
| `results/result_scan.png` | один скан: идеальные и зашумлённые точки в системе лидара |
| `results/result_uwb.png` | дальности A1–A4: идеал vs шум + смещение + пропуски |
| `results/result_localization_*.png` | локализация EKF: траектория и ошибки |
| `results/result_map_compare.png` | сетка занятости по истинной и оценённой позе + различия |
| `results/analysis_rmse.png` | RMSE локализации по сценариям анализа |
| `results/analysis_maps.png` | IoU и расстояние между картами по сценариям анализа |
| `results/analysis/summary.md` | таблица метрик и автоматические выводы |

Сырые данные прогона сохраняются в `results/plot_data.npz`. Повторная отрисовка без
запуска симуляции:

```bash
source /opt/ros/jazzy/setup.bash && source install/setup.bash
python3 tools/visualize.py --replot
```

## RViz

`navigator_description/config/navigator.rviz` задаёт вид сверху: модель робота, TF,
истинную траекторию и оценку EKF (`/estimate/odom`, `/estimate/path`), маркеры
полигона, два лидарных скана (`/scan_ideal`, `/scan_noisy`), карты сетки
занятости (`/map/estimate` включён, `/map/ground_truth` выключен по умолчанию),
а также выключенные по умолчанию `/slam/path`, `/slam/odom`, `/slam/markers` и
`/landmarks/markers` — их достаточно включить галочкой при запуске
`landmarks.launch.py` или `slam.launch.py`. Fixed Frame — `map`. В Windows 11 окно RViz открывается через WSLg; на headless-машине
можно снимать скриншоты через виртуальный дисплей:

```bash
sudo apt install -y xvfb imagemagick
Xvfb :99 -screen 0 1600x1000x24 &
export DISPLAY=:99
ros2 launch navigator_bringup simulation.launch.py
import -window root rviz.png
```

## Проблемы и решения

Типичные проблемы с sourcing, сборкой, DDS, RViz, топиками и инструментами
анализа описаны в [Диагностике](troubleshooting.md).
