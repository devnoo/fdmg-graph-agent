"""Chart generation tools using matplotlib."""

import json
import os
from datetime import datetime
from typing import Literal

import matplotlib.pyplot as plt
import matplotlib

# Use non-interactive backend for server environments
matplotlib.use("Agg")

# Brand color definitions
BRAND_COLORS = {
    "fd": {
        "primary": "#379596",
        "content": "#191919",
        "background": "#ffeadb",
    },
    "bnr": {
        "primary": "#ffd200",
        "content": "#000",
        "background": "#fff",
    },
}


def apply_brand_style(fig, ax, style: Literal["fd", "bnr"]):
    """
    Apply brand-specific styling to matplotlib figure and axes.

    Args:
        fig: Matplotlib figure object
        ax: Matplotlib axes object
        style: Brand style ('fd' or 'bnr')
    """
    colors = BRAND_COLORS[style]

    # Set background colors
    fig.patch.set_facecolor(colors["background"])
    ax.set_facecolor(colors["background"])

    # Set text colors
    ax.tick_params(colors=colors["content"], labelcolor=colors["content"])
    ax.xaxis.label.set_color(colors["content"])
    ax.yaxis.label.set_color(colors["content"])

    # Set spine colors
    for spine in ["bottom", "left", "top", "right"]:
        ax.spines[spine].set_color(colors["content"])

    # Remove top and right spines for cleaner look
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add subtle grid
    ax.grid(True, alpha=0.2, color=colors["content"], linestyle="-", linewidth=0.5)
    ax.set_axisbelow(True)


def matplotlib_chart_generator(
    data: str,
    chart_type: Literal["bar", "line"],
    style: Literal["fd", "bnr"],
    format: Literal["png", "svg"],
) -> str:
    """
    Generate a brand-styled chart using matplotlib.

    Args:
        data: JSON string of data points [{"label": "A", "value": 10}, ...]
        chart_type: Type of chart to generate ('bar' or 'line')
        style: Brand style to apply ('fd' or 'bnr')
        format: Output format ('png' or 'svg')

    Returns:
        Absolute path to the generated chart file

    Example:
        >>> data = '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        >>> filepath = matplotlib_chart_generator(data, "bar", "fd", "png")
        >>> print(filepath)
        /home/user/chart-20251106143000.png
    """
    # Parse data
    data_points = json.loads(data)
    labels = [point["label"] for point in data_points]
    values = [point["value"] for point in data_points]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Get brand colors
    colors = BRAND_COLORS[style]

    # Generate chart based on type
    if chart_type == "bar":
        ax.bar(labels, values, color=colors["primary"], edgecolor=colors["content"])
    elif chart_type == "line":
        ax.plot(
            labels,
            values,
            color=colors["primary"],
            marker="o",
            linewidth=2,
            markersize=8,
        )

    # Apply brand styling
    apply_brand_style(fig, ax, style)

    # Add labels (no title per requirements)
    ax.set_xlabel("", fontsize=10)
    ax.set_ylabel("", fontsize=10)

    # Adjust layout for better spacing
    plt.tight_layout()

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"chart-{timestamp}.{format}"
    filepath = os.path.abspath(filename)

    # Save figure
    plt.savefig(
        filepath,
        format=format,
        dpi=300 if format == "png" else None,
        bbox_inches="tight",
        facecolor=colors["background"],
    )

    # Close figure to free memory
    plt.close(fig)

    return filepath
