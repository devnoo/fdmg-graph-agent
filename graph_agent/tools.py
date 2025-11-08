"""Chart generation tools using matplotlib."""

import json
import os
import logging
import re
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


def sanitize_filename(name: str, max_length: int = 20) -> str:
    """
    Sanitize a string to be filesystem-safe for use in filenames.

    Applies the following transformations:
    - Convert to lowercase
    - Replace spaces and underscores with hyphens
    - Remove special characters (keep only a-z, 0-9, hyphen)
    - Remove accents/diacritics
    - Truncate to max_length characters
    - Ensure non-empty (return 'chart' if empty)

    Args:
        name: String to sanitize
        max_length: Maximum length of output (default: 20)

    Returns:
        Sanitized filename-safe string

    Examples:
        >>> sanitize_filename("Café sales")
        'cafe-sales'
        >>> sanitize_filename("Q1/Q2 Results")
        'q1-q2-results'
        >>> sanitize_filename("Year-over-year growth rate", max_length=20)
        'year-over-year-gro'
    """
    if not name:
        return "chart"

    # Convert to lowercase
    result = name.lower()

    # Replace common diacritics
    replacements = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
    }
    for diacritic, replacement in replacements.items():
        result = result.replace(diacritic, replacement)

    # Replace spaces, underscores, and slashes with hyphens
    result = re.sub(r'[\s_/]+', '-', result)

    # Remove all non-alphanumeric characters except hyphens
    result = re.sub(r'[^a-z0-9-]', '', result)

    # Remove consecutive hyphens
    result = re.sub(r'-+', '-', result)

    # Remove leading/trailing hyphens
    result = result.strip('-')

    # Truncate to max length (strip trailing hyphens after truncation)
    if len(result) > max_length:
        result = result[:max_length]
        result = result.rstrip('-')

    # Ensure non-empty
    if not result:
        result = "chart"

    logger.debug(f"sanitize_filename: '{name}' -> '{result}'")
    return result


def extract_logical_name(user_prompt: str, llm) -> str:
    """
    Extract a 1-2 word logical filename prefix from user prompt using LLM.

    This function uses Gemini to intelligently extract a short, meaningful
    name from the user's prompt. Works with both Dutch and English.

    Args:
        user_prompt: The user's original request/prompt
        llm: LLM instance to use for extraction

    Returns:
        Sanitized logical name (1-2 words), or 'chart' if extraction fails

    Examples:
        >>> extract_logical_name("Maak een grafiek van studieschuld data", llm)
        'studieschuld'
        >>> extract_logical_name("Q1=100, Q2=150, Q3=200", llm)
        'quarterly'
        >>> extract_logical_name("Create bar chart for monthly sales", llm)
        'sales'
    """
    logger.debug(f"extract_logical_name: Extracting from: {user_prompt[:100]}...")

    extraction_prompt = f"""Extract a 1-2 word filename prefix from the following text.
The prefix should summarize the main topic or subject of the data/chart.

Rules:
- Return ONLY the prefix, no explanation or extra words
- Use 1-2 words maximum
- Use lowercase
- Prefer nouns over verbs
- If the text mentions specific data (like "studieschuld", "sales", "revenue"), use that
- If it's generic data like "A=10, B=20", use "data" or describe the pattern (e.g., "quarterly" for Q1, Q2, Q3)

Examples:
- "Maak een grafiek van studieschuld data" -> studieschuld
- "Q1=100, Q2=150, Q3=200, Q4=180" -> quarterly
- "Amsterdam=500, Rotterdam=400, Utrecht=300" -> cities
- "Create a bar chart for monthly sales" -> sales
- "A=10, B=20, C=30" -> data

Text: {user_prompt}

Prefix:"""

    try:
        response = llm.invoke(extraction_prompt)
        extracted_name = response.content.strip().lower()
        logger.debug(f"extract_logical_name: LLM returned: '{extracted_name}'")

        # Clean up the response (remove quotes, periods, etc.)
        extracted_name = extracted_name.strip('"\'.,!? ')

        # Sanitize the extracted name FIRST (this handles special characters properly)
        sanitized_name = sanitize_filename(extracted_name)

        # Take only first 2 words after sanitization (split by hyphen)
        words = sanitized_name.split('-')[:2]
        sanitized_name = '-'.join(words)

        # If sanitization resulted in empty or very short string, use fallback
        if not sanitized_name or len(sanitized_name) < 2:
            logger.warning(f"extract_logical_name: Extracted name too short, using fallback")
            return "chart"

        logger.info(f"extract_logical_name: Final name: '{sanitized_name}'")
        return sanitized_name

    except Exception as e:
        logger.warning(f"extract_logical_name: Failed to extract name: {e}")
        return "chart"


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
    output_filename: str | None = None,
) -> str:
    """
    Generate a brand-styled chart using matplotlib.

    Args:
        data: JSON string of data points [{"label": "A", "value": 10}, ...]
        chart_type: Type of chart to generate ('bar' or 'line')
        style: Brand style to apply ('fd' or 'bnr')
        format: Output format ('png' or 'svg')
        output_filename: Optional custom filename (e.g., 'my_chart.png', 'charts/output.svg')
                        If not provided, uses timestamp-based name

    Returns:
        Absolute path to the generated chart file

    Example:
        >>> data = '[{"label": "A", "value": 10}, {"label": "B", "value": 20}]'
        >>> filepath = matplotlib_chart_generator(data, "bar", "fd", "png")
        >>> print(filepath)
        /home/user/chart-20251106143000.png
        >>> filepath = matplotlib_chart_generator(data, "bar", "fd", "png", "my_chart.png")
        >>> print(filepath)
        /home/user/my_chart.png
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

    # Determine output filepath
    if output_filename:
        # Custom filename provided
        logger.info(f"matplotlib_chart_generator: Using custom filename: {output_filename}")

        # Convert to Path object
        output_path = Path(output_filename)

        # Check if extension is provided
        if output_path.suffix:
            # Validate extension matches format
            expected_ext = f".{format}"
            if output_path.suffix.lower() != expected_ext:
                logger.warning(f"matplotlib_chart_generator: Extension mismatch - "
                             f"filename has '{output_path.suffix}', expected '{expected_ext}'. "
                             f"Using filename as-is.")
        else:
            # No extension provided, add one
            output_path = output_path.with_suffix(f".{format}")
            logger.debug(f"matplotlib_chart_generator: Added extension: {output_path}")

        # Make absolute if relative
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path

        # Create parent directories if they don't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"matplotlib_chart_generator: Ensured directory exists: {output_path.parent}")

        filepath = str(output_path)
    else:
        # Generate filename with timestamp (fallback)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"chart-{timestamp}.{format}"
        filepath = os.path.abspath(filename)
        logger.debug(f"matplotlib_chart_generator: Using timestamp-based filename: {filepath}")

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

    logger.info(f"matplotlib_chart_generator: Chart saved to: {filepath}")
    return filepath
