# Architecture Document: Graph Agent (MVP)

**Version:** 1.3 (Aligned with PRD v1.2)
**Author:** Architect

## 1. Overview & Guiding Principles

This document outlines the architecture for the **Graph Agent**, a CLI tool for journalists to create brand-compliant charts from data.

* **Guiding Principle:** A clean, modular "Agentic" architecture. The core logic (the "brain") is decoupled from the specific tools (parsing, charting) and the interface (CLI).
* **Core Technology:** The system is a **Python** application built using **LangGraph** as the central orchestrator, **Gemini** as the reasoning LLM, and **`click`** as the CLI framework.

---

## 2. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Orchestration** | **LangGraph** | A state machine (graph) is perfect for managing the complex, stateful logic of "Conversational" vs. "Direct" modes. |
| **Language Model** | **Google Gemini** | Provides the core intelligence for NLU (EN/NL), data extraction from text, and intent recognition. |
| **CLI Framework** | **`click`** | A simple, powerful library for creating the dual-mode (conversational REPL vs. direct command) CLI with its override flags. |
| **Chart Generation** | **`matplotlib`** | A robust, industry-standard library that provides full control over styling (for brand compliance) and supports both **SVG** and **PNG** output. |
| **Excel Parsing** | **`pandas`** | The standard for Excel I/O and data manipulation. |
| **Package Mgmt** | **`uv`** | A fast, modern Python package manager and virtual environment wrapper. |
| **Config Storage** | **`JSON` file** | A simple, human-readable file (`~/.config/graph-agent/settings.json`) for persistent user preferences (style, format). |

---

## 3. Component Architecture

The system is comprised of four primary components: **Interface**, **Agent Core**, **Tools**, and **Configuration**.



### 3.1. Interface (`cli.py`)

* This is the main entry point, built with **`click`**.
* It supports two primary interaction modes.

**1. Direct Mode (Stateless)**
* Invoked by passing a prompt string directly to the command.
* **Prompt Argument:** It accepts a main `prompt` string as a **`click.Argument`**.
* **Override Options:** It also accepts optional **`click.Option`** flags:
    * `--file <path>`
    * `--style <fd|bnr>`
    * `--format <png|svg>`
    * `--type <bar|line>`
    * `--output-file <path>`
* **Logic:** Gathers all arguments and invokes the Agent Core in a single, stateless run. The agent will be instructed to **prioritize the explicit flags** over any conflicting information found in the `prompt` string.

**2. Conversational Mode (Stateful)**
* Invoked by running `graph-agent` with **no arguments**.
* Starts a stateful REPL (Read-Eval-Print Loop).

### 3.2. Agent Core (The LangGraph State Machine)

This is the "brain" of the application, built with **LangGraph**. It defines the application's flow as a graph of nodes and conditional edges.

* **Language:** Per the de-scoped PRD, the agent will be **English-only** for the MVP. The AgentState will not include a language field, and no language detection tools will be implemented. All prompts and user-facing messages will be in English.



#### Key State (`GraphState`)
The graph will pass a central `GraphState` object between nodes, which will contain:
* `messages`: A list of chat messages.
* `interaction_mode`: 'conversational' or 'direct'.
* `user_prefs`: The loaded default style and format.
* `file_path`: The path to the file being processed.
* `input_data`: The final cleaned data block, as a JSON string.
* `chart_request`: A Pydantic object for the chart parameters.
* `output_filename`: `Optional[str] = None`: Stores the user's desired output filename, if specified.
* `final_filepath`: The path of the generated file.

#### Key Nodes (Functions)
1.  **`parse_intent`**: (Gemini Call) This is the central reasoning loop.
    * It determines intent (e.g., `make_chart`, `set_default`, `off_topic`).
    * It extracts data from text or a `file_path`.
    * It checks if `state.output_filename` is set (from the CLI flag).
    * If `state.output_filename` is `None`, it asks the LLM to check the user's query for a filename (e.g., "save as...") and updates the state if one is found.
2.  **`call_data_tool`**: (Tool Node) This node executes the `parse_excel_a1` tool if a file path is present.
3.  **`resolve_ambiguity`**: This is the logic hub that runs *after* data is loaded. It checks `chart_request` for missing info (type, style) based on the PRD logic.
4.  **`generate_chart_tool`**: (Tool Node) Calls the `matplotlib_chart_generator` tool.
5.  **`ask_clarification`**: (Gemini Call) If ambiguity is found in 'conversational' mode, this node generates an **English** question.
6.  **`report_error`**: (Terminal Node) If ambiguity is found in 'direct' mode, this node formats a clear **English** error message.
7.  **`reject_task`**: (Terminal Node) Politely rejects off-topic requests in **English**.

### 3.3. Tools (`tools.py`)

This toolset is simplified to match the A1-based parsing requirement.

1.  **`parse_excel_a1(file_path: str) -> str`**
    * **What it does:** Implements the "A1-Based" logic from PRD 4.2. It iterates through sheets, looking for the first sheet that contains a data block starting in cell A1. It reads this block (`pd.read_excel(..., header=0)`) and returns the data as a JSON string.
    * **Why:** This is a simple, deterministic parser for the MVP. It replaces the complex multi-tool agentic workflow, which is now on the backlog.
2.  **`matplotlib_chart_generator(data: str, type: str, style: str, output_filename: Optional[str]) -> str`**
    * **What it does:** Accepts the JSON string data, parses it (`pd.read_json(data)`), and uses `matplotlib` to generate the chart figure in the correct brand style.
    * **Filename Logic:**
        * If `output_filename` is provided, it uses that name (ensuring the correct `.png` or `.svg` extension).
        * If `output_filename` is `None`, it generates the default `chart-[timestamp].[ext]` filename.
    * **Returns:** It saves the file to disk and returns the absolute, final file path.

### 3.4. Configuration (`config.py`)

* A simple module to handle the persistent memory.
* `load_user_preferences()`: Reads the `settings.json` file.
* `save_user_preferences(style, format)`: Writes changes to the `settings.json` file.
* Will also store constants (e.g., `BRAND_COLORS`, `CONFIG_PATH`).

---

## 4. Data & Logic Flow

### Scenario 1: Direct Mode (Eval 5.3)

`graph-agent "geef me een grafiek voor fdmg_timeseries_example.xlsx" --output-file my_chart.svg`

1.  **CLI:** `click` parses the args.
    * `prompt` = "geef me een grafiek voor..."
    * `file_flag` = `None`
    * `output_filename_flag` = "my_chart.svg"
    * `interaction_mode` = 'direct'
2.  **Agent Core:** Invokes the graph. `GraphState` is pre-filled: `output_filename='my_chart.svg'`.
3.  **`parse_intent`**: (Gemini Call) The LLM analyzes the prompt and extracts `file_path='fdmg_timeseries_example.xlsx'`. It sees `output_filename` is already set, so it skips that check.
4.  **`call_data_tool`**: Calls `parse_excel_a1('fdmg_timeseries_example.xlsx')`. The tool finds the A1 data and returns a JSON string, which is saved to `GraphState.input_data`.
5.  **`resolve_ambiguity`**:
    * Checks `chart_type`: The data is a time-series, so it defaults to **line chart** (PRD 4.2).
    * Checks `brand_style`: No style is specified in the query or flags, and the user has no default. This is ambiguous.
6.  **Conditional Edge:** Ambiguity (`brand_style`) found in 'direct' mode. Routes to `report_error`.
7.  **`report_error`**: Prints `Error: Ambiguous request. Please specify style using --style.` and exits.

### Scenario 2: Conversational Mode (Eval 5.2 - Testprompt 1)

`graph-agent`
`> Geef me een grafiek met het aantal checkins per dag bij het OV: 0 Maandag = 4,1 0 Dinsdag = 4,2...`

1.  **CLI:** Starts REPL. Sets `interaction_mode` to 'conversational'.
2.  **Agent Core:** Invokes the graph.
3.  **`parse_intent`**: (Gemini Call) "User provided data directly in the text." The LLM extracts the data and populates `GraphState.input_data` with the (Maandag, 4.1), (Dinsdag, 4.2)... data.
4.  **`call_data_tool`**: No `file_path` was provided, so this node is skipped.
5.  **`resolve_ambiguity`**:
    * Checks `chart_type`: The data is categorical ("Maandag", "Dinsdag"...). PRD 4.2 states the agent must **ask**.
    * Checks `brand_style`: No style is specified, and user has no default. The agent must **ask**.
6.  **Conditional Edge:** Ambiguity found in 'conversational' mode. Routes to `ask_clarification`.
7.  **`ask_clarification`**: (Gemini Call) Generates a question.
8.  **CLI:** Prints (in English): "I have the data. What type of chart would you like (bar or line)? And which style (FD or BNR)?"
9.  Graph "pauses".

---

## 5. Architectural Decisions & Notes

* **Multilingual (English-Only MVP):**
    * **Input:** Gemini will handle both EN and NL user queries for *data extraction*.
    * **Output:** All *agent-generated* responses (errors, clarifications, guardrails) will be in **English** per PRD v1.2.
* **Guardrails:** The "off-topic" guardrail will be the first check in `parse_intent`, routing directly to `reject_task`.
* **File Naming:** The new file output logic is implemented. The priority is **CLI Flag (`--output-file`) > In-Query ("save as...") > Fallback (`chart-[timestamp].[ext]`)**. The logical filenaming feature is now on the backlog.
* **Excel Parsing (A1-Based):** The architecture is now significantly simpler. The complex, multi-tool agentic workflow for data finding has been removed and placed on the backlog, per PRD v1.2.