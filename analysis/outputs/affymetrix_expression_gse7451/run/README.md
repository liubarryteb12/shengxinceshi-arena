# Current P1 run pointer

This directory contains the latest materialized run configuration, summary and (for `matrix_only`) the series-matrix extraction. The semantic run ID is stored inside `summary.json` and is also recorded in `manifest.yaml`, `analysis/_runs/` and the P1→P2/P4 interfaces.

Older run records, including failed local raw-CEL attempts, remain under `analysis/_runs/` and their logs under `../logs/`. They must not be treated as successful scientific results.
