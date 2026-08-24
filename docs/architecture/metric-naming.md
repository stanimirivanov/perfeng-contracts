# Metric Naming Conventions

## Overview

All performance metrics follow a hierarchical naming convention to ensure consistency and enable automated processing.

## Format

```text
<prefix>.<service>.<component>.<metric_name>
```

## Prefixes

| Prefix   | Purpose                      | Example                                  |
| -------- | ---------------------------- | ---------------------------------------- |
| `api.`   | API endpoint metrics         | `api.checkout.cart.get.duration_p95`     |
| `biz.`   | Business transaction metrics | `biz.checkout.submit_to_confirmation.ms` |
| `res.`   | Resource utilization metrics | `res.checkout-service.cpu.percent`       |
| `ui.`    | Browser/UI metrics           | `ui.search.action_to_visible_ms`         |
| `k8s.`   | Kubernetes metrics           | `k8s.pod.startup.latency_p95`            |
| `infra.` | Infrastructure metrics       | `infra.node.disk.iops`                   |

## Metric Names

| Suffix                         | Meaning       | Unit            |
| ------------------------------ | ------------- | --------------- |
| `_duration`                    | Time duration | milliseconds    |
| `_p50`, `_p90`, `_p95`, `_p99` | Percentiles   | varies          |
| `_rate`                        | Rate          | varies          |
| `_count`                       | Count         | integer         |
| `_throughput`                  | Throughput    | requests/second |
| `_size`                        | Size          | bytes           |

## Examples

### API Metrics

```text
api.checkout.cart.get.duration_p95
api.checkout.checkout.post.duration_p99
api.search.query.get.duration_p95
api.account.user.put.duration_mean
```

### Business Metrics

```text
biz.checkout.submit_to_confirmation.duration_p95
biz.search.query_to_results.duration_p95
biz.account.login_to_dashboard.duration_p90
```

### Resource Metrics

```text
res.checkout-service.cpu.percent
res.checkout-service.memory.mb
res.database.connections.active
```

## Rules

1. **Lowercase**: All metric names are lowercase
2. **Underscores**: Words separated by underscores
3. **No special characters**: Only `[a-z0-9_.]` allowed
4. **Hierarchical**: Most general to most specific
5. **Consistent units**: Same metric always uses same unit
6. **Direction**: Each metric has a defined direction (lower-is-better or higher-is-better)
