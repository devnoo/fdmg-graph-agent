"""Chart generation tools using matplotlib."""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import matplotlib
import pandas as pd

# Use non-interactive backend for server environments
matplotlib.use("Agg")

# Configure logging
logger = logging.getLogger(__name__)

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


def parse_excel_a1(file_path: str) -> str:
    """
    Parse Excel file using A1-based logic.

    Expects 2-column format at A1:
    - Column 1 (A): Labels (text)
    - Column 2 (B): Values (numbers)
    - Row 1: Optional headers (will be detected and skipped)

    For multi-sheet files, scans sheets in order and uses the first sheet
    that contains valid data starting at A1.

    Args:
        file_path: Path to Excel file (.xlsx or .xls), can be relative or absolute

    Returns:
        JSON string of data: '[{"label": "...", "value": ...}, ...]'

    Raises:
        ValueError: If file not found, invalid format, or no valid data at A1

    Example:
        >>> data_json = parse_excel_a1("sales.xlsx")
        >>> print(data_json)
        [{"label": "Q1", "value": 120}, {"label": "Q2", "value": 150}]
    """
    logger.debug(f"parse_excel_a1: Processing file: {file_path}")

    # Resolve relative paths from current working directory
    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path

    logger.debug(f"parse_excel_a1: Resolved path: {path}")
    logger.debug(f"parse_excel_a1: Current working directory: {Path.cwd()}")

    # Validate file exists
    if not path.exists():
        error_msg = f"Error: Could not find file '{file_path}'"
        logger.error(f"parse_excel_a1: {error_msg}")
        logger.error(f"parse_excel_a1: Resolved to: {path}, which does not exist")
        raise ValueError(error_msg)

    # Validate file extension
    if path.suffix.lower() not in ['.xlsx', '.xls']:
        error_msg = f"Error: File must be .xlsx or .xls format"
        logger.error(f"parse_excel_a1: {error_msg}, got {path.suffix}")
        raise ValueError(error_msg)

    logger.debug(f"parse_excel_a1: Reading Excel file: {path}")

    # Read Excel file
    try:
        excel_file = pd.ExcelFile(path)
        logger.debug(f"parse_excel_a1: Found {len(excel_file.sheet_names)} sheet(s): {excel_file.sheet_names}")
    except Exception as e:
        error_msg = f"Error: Failed to read Excel file: {str(e)}"
        logger.error(f"parse_excel_a1: {error_msg}")
        raise ValueError(error_msg)

    # Iterate through sheets to find data at A1
    for sheet_name in excel_file.sheet_names:
        logger.debug(f"parse_excel_a1: Checking sheet '{sheet_name}'")

        try:
            # Read first 2 columns, up to 100 rows
            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
                header=0,  # Assume first row is header
                usecols=[0, 1],  # Only read first 2 columns
                nrows=100  # Limit rows for performance
            )

            logger.debug(f"parse_excel_a1: Sheet '{sheet_name}' shape: {df.shape}")

            # Check if valid data exists (at least 1 row, 2 columns)
            if df.shape[0] > 0 and df.shape[1] == 2:
                # Convert to JSON format
                data = []
                for idx, row in df.iterrows():
                    try:
                        label = str(row.iloc[0])
                        # Remove trailing .0 from numeric labels like "2020.0" -> "2020"
                        if label.endswith(".0"):
                            label = label[:-2]
                        # Handle various number formats
                        value = float(row.iloc[1])
                        data.append({"label": label, "value": value})
                    except (ValueError, TypeError) as e:
                        # Skip rows with invalid data
                        logger.warning(f"parse_excel_a1: Skipping row {idx} due to invalid data: {e}")
                        continue

                if data:
                    logger.info(f"parse_excel_a1: Successfully extracted {len(data)} data points from sheet '{sheet_name}'")
                    return json.dumps(data)

        except Exception as e:
            logger.warning(f"parse_excel_a1: Failed to parse sheet '{sheet_name}': {e}")
            continue

    # If we get here, no valid data was found
    error_msg = "Error: No valid data found at cell A1 in any sheet"
    logger.error(f"parse_excel_a1: {error_msg}")
    raise ValueError(error_msg)


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
