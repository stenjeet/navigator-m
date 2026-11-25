# Руководство по проверке

[English](../en/verification.md) | **Русский**

Это руководство описывает, как проверить стек Navigator-M: автоматические
тесты, статические проверки, runtime smoke-проверки, ожидаемый вывод и
известные ограничения.

Все команды выполняются из корня репозитория. Сначала подготовьте окружение:

```bash
cd ~/navigator-m
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

Команда `ros2 launch` занимает терминал. Команды `ros2 topic`, `ros2 node` и
`tf2_echo` запускайте во втором терминале с тем же окружением.

## Матрица тестов

| Область | Команда | Ожидаемо |
|---|---|---|
| Локализация | `PYTHONPATH=src/navigator_localization:src/navigator_sim python3 -m unittest discover -s src/navigator_localization/test -v` | 12 тестов, OK |
| SLAM и анализ | `PYTHONPATH=src/navigator_slam:src/navigator_sim python3 -m unittest discover -s src/navigator_slam/test -v` | 177 тестов, OK |
| Геометрия симулятора | `PYTHONPATH=src/navigator_sim:src/navigator_description python3 -m unittest discover -s src/navigator_sim/test -v` | 8 тестов, OK |
| Синтаксис Python | `python3 -m py_compile $(find src tools -name '*.py')` | без ошибок |
| Документация | `python3 tools/check_docs.py` | API и пары EN/RU согласованы |
| ROS-пакеты | `colcon test && colcon test-result --verbose` | все пакеты проходят |
| Окружение | `ros2 doctor` | без критических проблем |

Чистые Python-тесты не импортируют `rclpy` и сообщения ROS, поэтому запускаются
на машине без ROS. Всего 197 тестов: 177 в `navigator_slam`, 12 в
`navigator_localization` и 8 в `navigator_sim`.

## Статические проверки

Тесты также проверяют статическую сцену:

- звенья, сочленения и смещения датчиков в URDF;
- геометрию полигона, зазоры препятствий и границы арены;
- палитру сцены и определения ориентиров;
- согласованность `world.py`, URDF и модели лидара.

Полная статическая проверка:

```bash
PYTHONPATH=src/navigator_sim:src/navigator_description \
  python3 -m unittest discover -s src/navigator_sim/test -v
```

## Runtime-проверки

### Симуляция и описание робота

```bash
ros2 launch navigator_bringup simulation.launch.py use_rviz:=false
```

Во втором терминале:

```bash
ros2 node list
ros2 topic hz /ground_truth/odom     # ~20 Гц
ros2 topic hz /scan_ideal            # ~10 Гц
ros2 topic hz /uwb/noisy_ranges      # ~10 Гц
ros2 run tf2_ros tf2_echo map base_footprint
```

Ожидаемо: шесть узлов без узла локализации; публикуется
`map -> odom -> base_footprint`; поза движется по квадрату
`(1.5, 1.5) -> (5.5, 1.5) -> (5.5, 5.5) -> (1.5, 5.5) -> (1.5, 1.5)`
со скоростью `v = 0.35 м/с` и `omega = 0.60 рад/с`.

Статичный показ робота и полигона:

```bash
ros2 launch navigator_bringup display.launch.py use_rviz:=false
ros2 topic echo --once --qos-durability transient_local /robot_description | head
ros2 topic echo --once /polygon_markers | head
```

### EKF-локализация

```bash
ros2 launch navigator_bringup localization.launch.py use_rviz:=false
```

Во втором терминале:

```bash
ros2 topic hz /estimate/odom          # ~20 Гц
ros2 topic echo --once /estimate/odom
ros2 topic echo --once /estimate/error   # x, y, yaw
```

Ожидаемо: оценка следует за истинной позой с ошибкой в несколько сантиметров
на зашумлённых дальностях СШП. Курс по одной метке в статике не наблюдается и
уточняется на поворотах.

Метрики и графики:

```bash
./run_localization_metrics.sh          # 62 с
./run_localization_metrics.sh 90       # 90 с
```

Результаты: `results/result_localization_trajectory.png`,
`results/result_localization_error.png` и RMSE в консоли.

### Сетка занятости

```bash
ros2 launch navigator_bringup mapping.launch.py use_rviz:=false pose_source:=both
```

Во втором терминале:

```bash
ros2 topic hz /map/estimate                 # ~1 Гц
ros2 topic echo --once /map/estimate        # 180 x 180, data -1/0/100
ros2 topic echo --once /map/ground_truth
```

Ожидаемо: две карты `nav_msgs/OccupancyGrid` с разрешением `0.05 м` и
значениями `-1` (неизвестно), `0` (свободно) и `100` (занято). Карта по
оценке EKF должна совпадать с эталонной в пределах нескольких сантиметров.

Сравнение карт:

```bash
./run_map_compare.sh
```

Результаты: `results/result_map_compare.png`, IoU занятых ячеек, доля
совпавших ячеек и среднее/максимальное расстояние между занятыми ячейками.
Обе карты строятся по одним и тем же сканам, поэтому различие отражает только
ошибку позы.

### Детектор ориентиров

```bash
ros2 launch navigator_bringup landmarks.launch.py use_rviz:=false
```

Во втором терминале:

```bash
ros2 topic hz /landmarks/observations       # ~10 Гц
ros2 topic echo --once /landmarks/observations
ros2 topic echo --once /landmarks/map       # id и ковариации
ros2 topic echo --once /landmarks/markers
```

Ожидаемо: 1-4 наблюдения на скан в системе `base_footprint` и стабильная
карта из четырёх подтверждённых ориентиров после полного круга. Кандидат
подтверждается только после нескольких согласованных наблюдений, поэтому углы
стен не становятся постоянными ориентирами.

Проверка детектора без ошибки локализации:

```bash
ros2 launch navigator_bringup landmarks.launch.py \
  pose_topic:=/ground_truth/odom use_rviz:=false
```

### EKF-SLAM

```bash
ros2 launch navigator_bringup slam.launch.py use_rviz:=false
```

Во втором терминале:

```bash
ros2 topic hz /slam/odom                 # ~20 Гц
ros2 topic echo --once /slam/landmarks   # четыре ориентира с id
ros2 topic echo --once /slam/error       # ошибка относительно истины
```

Ожидаемо: четыре ориентира со стабильными id и ошибка позы в сантиметровом
диапазоне после замыкания петли.

Unit-тест замыкания петли:

```bash
PYTHONPATH=src/navigator_slam:src/navigator_sim python3 -m unittest \
  src.navigator_slam.test.test_ekf_slam.TestLoopClosure.test_double_loop_closes_and_keeps_the_ids -v
```

Тест выполняет два круга, проверяет, что число ориентиров остаётся равным
четырём и дубликаты id не появляются.

Runtime-проверка замыкания: поставьте `loops: 2` в
`navigator_sim/config/motion.yaml` и запустите `slam.launch.py`. После второго
круга `/slam/landmarks` должен сохранить те же четыре id.

### Сценарный анализ

```bash
./run_analysis.sh --quick          # 3 сценария по 30 с
./run_analysis.sh                  # 10 сценариев по 62 с
python3 tools/analysis.py --replot # без ROS, из сохранённого npz
```

Результаты:

| Файл | Содержимое |
|---|---|
| `results/analysis/summary.md` | RMSE, IoU, расстояния между картами и выводы |
| `results/analysis/summary.csv` | те же метрики в машиночитаемом виде |
| `results/analysis_rmse.png` | RMSE позы и курса по сценариям |
| `results/analysis_maps.png` | IoU и расстояние между картами по сценариям |
| `results/analysis/analysis_data.npz` | данные для `--replot` |

Контрольный вывод `./run_analysis.sh --quick` с прогревом 3 с:

| Сценарий | RMSE позы [м] | RMSE курса [°] | макс. \|e\| [м] | IoU занятых | Среднее расстояние [м] |
|---|---|---|---|---|---|
| baseline | 0.039 | 1.19 | 0.100 | 0.337 | 0.027 |
| uwb_sigma_0.10 | 0.045 | 1.36 | 0.101 | 0.321 | 0.027 |
| dropout_0.25 | 0.040 | 1.14 | 0.096 | 0.382 | 0.026 |

Точные значения зависят от таймингов и платформы, но порядок величины должен
сохраняться: несколько сантиметров RMSE положения и около одного градуса
RMSE курса.

## Чек-лист приёмки

- [ ] `colcon build --symlink-install` сообщает о шести пакетах.
- [ ] Все три набора тестов проходят: всего 197 тестов.
- [ ] `py_compile` и `colcon test` завершаются без ошибок.
- [ ] Симуляция публикует истинную позу, СШП, лидар и TF с ожидаемыми частотами.
- [ ] Локализация публикует `/estimate/odom` и ограниченную `/estimate/error`.
- [ ] Картография строит сетки `180 x 180` для обоих источников позы.
- [ ] Детектор публикует наблюдения и четыре стабильных ориентира на карте.
- [ ] EKF-SLAM публикует `/slam/odom`, четыре ориентира и ограниченную ошибку.
- [ ] `./run_analysis.sh --quick` записывает summary, CSV и оба графика.
- [ ] Для сборки не нужны сгенерированные файлы; `results/` существует только локально.

## Известные ограничения

- **Курс по СШП.** Одна метка в статике ограничивает только положение. Курс
  уточняется движением и поворотами; это свойство модели, а не дефект.
- **Общие сканы при сравнении карт.** Обе карты строятся по одним и тем же
  лидарным сканам, поэтому их различие изолирует ошибку позы и не измеряет шум
  скана.
- **Покрытие ROS-обёрток.** Unit-тесты покрывают чистые математические модули.
  ROS-узлы проверяются launch-файлами и командами `ros2 topic`, а не
  unit-тестами.
- **Нет физики столкновений.** Столкновения не моделируются. Геометрия
  полигона проверяется на зазор не менее `0.45 м` до траектории.
- **Владение TF.** Только `motion_node` публикует `odom -> base_footprint`.
  Локализация и SLAM публикуют позы в топики и не транслируют TF.
- **СШП-якоря и лидар.** Радио-якоря не входят в лидарную геометрию; они видны
  только как маркеры.
- **Задержка ориентиров.** Наблюдения применяются по текущей позе фильтра без
  интерполяции на штамп скана. На скорости `0.35 м/с` это даёт несколько
  сантиметров ошибки.
- **Шум процесса.** `Q` задаётся на один шаг прогноза и не масштабируется на
  `dt`. При штатном таймере 20 Гц это постоянный шум на шаг.
- **Смещения СШП.** Модель датчика содержит смещения по якорям, а фильтр
  считает их нулевыми, поэтому часть систематической ошибки остаётся
  нескомпенсированной.
- **Дискретное время.** Симулятор использует фиксированный шаг таймера и не
  использует `/clock`. Геометрия траектории детерминирована, но задержки
  callback-ов могут немного сдвигать привязку ко времени между запусками.
- **Область анализа.** Сценарная таблица варьирует шум СШП, пропуски, отказы и
  раскладку якорей; шум лидара зафиксирован на `0.02 м`.
- **Сгенерированные артефакты.** Рисунки и метрики в `results/` не хранятся в
  git и должны пересоздаваться локально.
