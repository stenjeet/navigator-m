# Algorithms

**English** | [Русский](../ru/algorithms.md)

This document describes the estimation and mapping algorithms used by the
workspace. All modules are pure Python and are covered by unit tests.

## Notation

- `mu`, `x` — state estimate.
- `Sigma`, `P` — state covariance.
- `F`, `H` — process and measurement Jacobians.
- `Q`, `R` — process and measurement noise covariances.
- `z` — measurement vector.
- `dt` — prediction step.
- `v`, `omega` — commanded linear and angular velocity.

## EKF localization

Module: `navigator_localization/ekf.py`, ROS wrapper: `ekf_node.py`.

### State and prediction

The filter estimates the planar pose of `base_footprint` in `map`:

```text
mu = [x, y, theta]^T
```

Prediction uses the differential-drive model and the commanded velocities from
`/cmd_vel`:

```text
x     += v * dt * cos(theta)
y     += v * dt * sin(theta)
theta += omega * dt
```

The process Jacobian is

```text
F = [1, 0, -v * dt * sin(theta)]
    [0, 1,  v * dt * cos(theta)]
    [0, 0,        1           ]
```

and the covariance is propagated as `P = F P F^T + Q`.

### UWB update

For an anchor `(ax, ay, az)` and tag offset `(dx, dy, dz)` in `base_link`, the
tag position in `map` is

```text
tx = x + dx * cos(theta) - dy * sin(theta)
ty = y + dx * sin(theta) + dy * cos(theta)
tz = dz
```

The predicted range is the 3D distance to the anchor:

```text
r = sqrt((tx - ax)^2 + (ty - ay)^2 + (tz - az)^2)
```

The measurement Jacobian row has non-zero entries only in the robot block:

```text
H = [ (tx - ax) / r, (ty - ay) / r, dr/dtheta ]
```

`dr/dtheta` includes the rotation of the tag offset. Invalid and `NaN` ranges
are dropped before the batch update. Each update uses the Joseph form

```text
P = (I - K H) P (I - K H)^T + K R K^T
```

which keeps `P` symmetric positive semi-definite, and wraps the heading to
`(-pi, pi]`.

### Observability

A single UWB tag at rest constrains only the tag position. The heading is not
observable from ranges alone, so it is corrected by motion and turns. This is a
physical property of the model and is covered by a dedicated test.

## Occupancy grid

Module: `navigator_slam/occupancy_grid.py`, ROS wrapper:
`occupancy_grid_node.py`.

### Log-odds update

Each cell stores occupancy in log-odds:

```text
l = log(p / (1 - p))
```

For every valid beam, cells along the ray receive free evidence and the end
cell receives occupied evidence:

```text
hit  : l += log(p_occupied / (1 - p_occupied))
free : l += log(p_free     / (1 - p_free))
```

The result is clamped to `[log_odds_min, log_odds_max]`, so old evidence can
still be overridden and no measurement dominates forever.

### Ray traversal

The beam is sampled with a step of `resolution / 2` (half a cell by default).
Touched cells are deduplicated, and the traversal is vectorised over all beams.
A cell hit by one beam and merely crossed by another is treated as occupied for
that scan.

### Publishing

Log-odds are converted back to probability and thresholded:

| Output | Condition |
|---|---|
| `100` occupied | `p >= occupied_threshold` |
| `0` free | `p <= free_threshold` |
| `-1` unknown | otherwise |

The default grid covers `-0.5..8.5 m` in both axes with `0.05 m` cells, which
gives `180 x 180` cells.

### Map comparison

`tools/map_compare.py` compares two grids with:

- occupied-cell IoU;
- agreement among cells known in both maps;
- mean and maximum distance from occupied cells of one map to the nearest
  occupied cell of the other;
- counts of cells occupied only in one map.

Distance is the primary metric: thin walls and landmarks occupy one or two
cells, so IoU is very sensitive to a one-cell shift.

## Landmark detection and association

Module: `navigator_slam/landmark_detection.py`, ROS wrapper:
`landmark_node.py`.

### Scan segmentation

1. Every finite beam inside `[min_range, max_range]` becomes a point in
   `base_footprint`. The lidar offset is added to the beam endpoint.
2. The scan is split where the range jump exceeds
   `jump_threshold + |angle_increment| * mean_range`.
3. Short gaps of invalid beams are bridged, and the first and last cluster are
   merged across the 360-degree scan boundary.

### Circle test

A cluster is accepted when:

- it has `min_points..max_points` beams;
- its width is below `max_cluster_width`;
- a circle with radius in `radius_min..radius_max` fits with a radial RMS
  residual below `max_residual`.

Short arcs are ill-conditioned for the algebraic least-squares circle fit, so
the detector falls back to a chord/sagitta arc fit. A flat wall has almost no
sagitta, so its fitted radius becomes very large and the cluster is rejected.
The radius window removes the 0.30 m and 0.42 m cylinders, and the width limit
removes walls and the box obstacle.

### Observation covariance

For `n` points, radial residual `res` and cluster half-width `h`:

```text
range_variance   = (sigma_range^2 + bias^2) / n + res^2 + h^2
bearing_variance = sigma_bearing^2
                   + (sigma_range^2 + bias^2) / (n * range^2)
                   + angle_increment^2 / 12
```

The `h^2` term covers the centre uncertainty of a short arc.

### Association

Observations are matched to known landmarks by the Mahalanobis distance of
range and bearing. The gate is a chi-square threshold for two degrees of
freedom (`9.21` for 99 %). Association is greedy by smallest distance, and each
landmark and each observation is used at most once per scan. Unmatched
observations receive a new id.

### Candidate confirmation

A candidate enters the map only after `min_hits` consistent sightings within
`tentative_gate`. A real landmark is re-observed hundreds of times, while a
wall corner fitted as a small circle appears only a few times. The candidate
buffer is bounded by `max_tentative_tracks`.

## EKF-SLAM

Module: `navigator_slam/ekf_slam.py`, ROS wrapper: `ekf_slam_node.py`.

### State

The joint state contains the robot pose and every landmark:

```text
mu    = [x, y, theta, m1x, m1y, ..., mNx, mNy]
Sigma = cov(mu)                       # (2N + 3) x (2N + 3)
```

The cross-correlations between the robot and the landmarks are what turn a
re-observed landmark into a pose correction (loop closure).

### Prediction and UWB update

Prediction is the same differential-drive model as the localization EKF, with
a full process Jacobian. `Q` is non-zero only in the robot block; landmark
blocks grow through the cross-covariances. UWB updates reuse the range model
from the localization EKF, including the tag offset and dropout handling.

### Landmark update

For a landmark at `(mx, my)`, the predicted observation is

```text
d     = hypot(mx - x, my - y)
alpha = wrap(atan2(my - y, mx - x) - theta)
h     = [d, alpha]
```

The Jacobian has non-zero blocks for the robot pose and the associated
landmark. The covariance update uses the Joseph form.

### Initialisation

A new landmark is initialised from the inverse observation model at the current
robot pose:

```text
mx = x + range * cos(theta + bearing)
my = y + range * sin(theta + bearing)
```

The new block and its cross-covariances to the whole state are filled from the
robot Jacobian, so later observations of other landmarks keep the correct
correlations. The diagonal is lower-bounded by `initial_landmark_std^2`.

### Association and confirmation

Association uses the joint innovation covariance (robot block, landmark block
and cross terms) plus the model floor of the detector covariance. A candidate
enters the joint state only after `min_landmark_hits` consistent sightings
within `tentative_gate`. This prevents wall corners from becoming phantom
landmarks.

### Loop closure

After a closed trajectory, the same landmarks are re-observed. Their
cross-correlations update the robot pose and reduce drift. The unit test
`TestLoopClosure.test_double_loop_closes_and_keeps_the_ids` drives two loops
and verifies that four ids remain and no duplicates appear.

## Scenario analysis

Module: `tools/analysis.py`.

The tool generates alternative `sensors.yaml` and `ekf.yaml` files for a list of
scenarios, launches the mapping stack headless, records `/estimate/error` and
the final occupancy grids, and aggregates:

- position and heading RMSE;
- maximum absolute pose error after a warm-up window;
- occupied-cell IoU;
- mean distance between the estimated and reference maps.

The built-in profile covers UWB noise levels, filter/model mismatch, dropouts,
a UWB outage window and alternative anchor layouts. Lidar noise is fixed in
the default profile.

## Related documentation

- [Architecture](architecture.md) — data flow, frames and topics.
- [Configuration](configuration.md) — parameters that control these algorithms.
- [Verification](verification.md) — tests and expected results.
- [Troubleshooting](troubleshooting.md) — common runtime problems.
