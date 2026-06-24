from typing import Any


def render_metric_lines(metrics: dict[str, Any]) -> list[str]:
    def fmt(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.4f}"

    theta = metrics["theta_deg"]
    return [
        f"- Precision@{theta:.2f} deg: {fmt(metrics.get('precision_at_theta'))}",
        f"- Recall@{theta:.2f} deg: {fmt(metrics.get('recall_at_theta'))}",
        f"- Geodesic MAE: {fmt(metrics.get('geodesic_mae_deg'))} deg",
        f"- P95 geodesic error: {fmt(metrics.get('p95_error_deg'))} deg",
        f"- Error jitter: {fmt(metrics.get('jitter_deg'))} deg",
    ]
