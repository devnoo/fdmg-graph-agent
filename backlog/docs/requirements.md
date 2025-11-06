# Product Requirements Document: Graph Agent (MVP)

**Version:** 1.1 (Final)
**Owner:** [Your Name]
**Stakeholders:** [Journalists, Editors, Infographics Team]

---

## 1. Project Vision & Goals

### 1.1. Problem Statement
FDMG journalists ("Chantal") need to create simple, brand-compliant bar and line charts from basic data (text or Excel) for their articles. This process is currently manual, slow, and requires them to either use complex tools or wait for the infographics team, creating a bottleneck.

### 1.2. Product Vision
To provide a simple, fast, and reliable AI agent that autonomously converts data (from text or Excel) into publication-ready graphs in the correct FD or BNR brand style, directly from a CLI.

### 1.3. Business Goal
To significantly speed up the creation of publication-ready diagrams, reducing manual labor and TTM (Time to Market) for articles on the website or in the paper. A secondary goal is to ensure all simple charts are 100% compliant with FD/BNR branding.

---

## 2. User Personas

### 2.1. Chantal (Primary Persona)
* **Role:** Journalist (FD or BNR)
* **Goal:** To quickly add a data visualization (e.g., a simple bar chart of poll results) to her article to make it more impactful.
* **Technical Skill:** Low to Medium. Comfortable with Office (Excel, Word), but not a programmer or data analyst. Uses a CLI if given clear instructions.
* **Frustration:** "Wasting time in Excel or waiting for the design team (infographics) for a simple bar chart."

---

## 3. Core Features

*This section lists the primary capabilities of the agent.*

* **Data Input (Text):** The agent can parse data from natural language text.
* **Data Input (Excel):** The agent can parse data from an Excel file.
* **Chart Generation:** The agent creates two types of charts: Bar and Line.
* **Automatic Brand Styling:** The agent automatically styles charts in the FD or BNR brand colors.
* **Persistent Style Memory:** The agent remembers the user's preferred brand style (FD or BNR) and output format (PNG/SVG).
* **Task Guardrails:** The agent will only perform tasks related to graph creation and will politely refuse all other requests.
* **File-based Chart Output:** The agent saves the final chart as a PNG/SVG file and returns the file path to the user.
* **Multilingual Support:** The agent understands and responds in both Dutch and English.

---

## 4. Requirements

*These are the detailed technical and functional specifications derived from the project brief.*

### 4.1. Functional Requirements

* **Interface:**
    * The agent must support two distinct interaction modes via the CLI:
    * **1. Conversational Mode:** A stateful, interactive session (like a chatbot) where the agent can ask clarification questions and the user can respond.
    * **2. Direct Command Mode:** A stateless, single-shot command (e.g., `graph-agent --prompt "..."`) that executes, outputs a file (or an error), and exits.
    * A web interface is a potential alternative but secondary for the MVP.

* **Language Support:**
    * **Input Language:** The agent **must** be able to understand and process queries in both **English** and **Dutch**.
    * **Output Language:** The agent's text-based responses (e.g., clarification questions, error messages, final file path confirmation) **must** be in the same language as the user's last query.

* **Input Types:**
    * **Free Text:** The agent must be able to parse data from natural language queries (see Test Prompts 1 & 2).
    * **Excel File:**
        * The agent must accept `.xlsx` or `.xls` files as input.
        * The agent **must** support file references via both **relative** (e.g., `data.xlsx`) and **absolute** (e.g., `/Users/chantal/Documents/data.xlsx`) paths.

* **Supported Chart Types:**
    * Line Chart
    * Bar Chart

* **Output Types:**
    * PNG (raster)
    * SVG (vector)

* **File Output Logic:**
    * The agent **must** save the generated graph (PNG or SVG) as a file on disk.
    * The agent **must** return the full file path of the saved chart to the user as its final output.
    * The agent **must** generate a logical filename for the chart.
    * The filename format **must** be: `[logical_name]-[timestamp].[ext]` (e.g., `studieschuld-20251106110500.png`). The `logical_name` should be a one- or two-word summary derived from the prompt (e.g., "checkins", "studieschuld").

* **Task Guardrails:**
    * The agent **must** reject any tasks that fall outside the scope of "making a graph."
    * The agent should respond with a polite, explanatory message when rejecting a task.
    * The agent should only use text output for clarification questions or explanations.

* **Memory:**
    * **Session Memory:** The agent should remember context within a single session.
    * **Persistent Memory:** The agent must have a simple persistent memory to store the user's preferred **style** (FD or BNR) and **output format** (PNG or SVG).

### 4.2. Business Logic Details

* **Interaction Mode Logic (Handling Ambiguity):**
    * The agent's behavior for handling ambiguity (e.g., missing chart type, multiple Excel sheets, missing style) depends entirely on its interaction mode.
    * **In Conversational Mode:** The agent will follow the "ask the user" logic defined below.
    * **In Direct Command Mode:** The agent **cannot** ask questions. If a query is ambiguous and cannot be resolved by the logic, the agent **must fail** with a clear error message (e.g., "Error: Ambiguous request. Please specify chart type using --type.").

* **Chart Type Selection Logic:**
    1.  The agent will first check if the user explicitly requested a "bar" or "line" chart.
    2.  If no type is specified, the agent will analyze the data. If it detects a clear time-series (e.g., years, months, dates), it will default to a **line chart**.
    3.  If the data is categorical (e.g., days of the week, product names) and no type is specified, the agent will **ask the user** (in Conversational Mode) or **fail** (in Direct Command Mode).

* **Excel File Parsing Logic:**
    1.  **Sheet Selection (Single Sheet):** If the uploaded Excel file contains only **one sheet**, the agent will parse that sheet for data.
    2.  **Sheet Selection (Multiple Sheets):** If the file contains **multiple sheets**, the agent will scan all of them to find a suitable data block.
        * If **exactly one sheet** contains a clear data block (as defined below), the agent will use it automatically.
        * If **multiple sheets** (or **no sheets**) contain a clear data block, the agent will **ask the user** (in Conversational Mode) or **fail** (in Direct Command Mode).
    3.  **Data Block Finding (Flexible Location):** When scanning any sheet, the agent must intelligently **locate a two-column (Label, Value) data block**. This search must be flexible, meaning it can find the data block *anywhere* on the sheet (not just starting in A1) and should correctly identify its headers, if present.

* **Style Selection & Memory Logic:**
    1.  The agent must manage two persistent memory concepts: a **Default Style** (long-term preference) and a **Last Used Style** (most recent).
    2.  When a user requests a chart, the agent **must** follow this priority order to determine which style (FD or BNR) to apply:
        * **Priority 1: Style in Query:** If the user specifies a style in the current prompt (e.g., "Make an FD bar chart..."), that style is used. This choice also updates the *Last Used Style* in memory.
        * **Priority 2: Default Style:** If no style is in the query, the agent checks if the user has a *Default Style* saved. If yes, that style is used.
        * **Priority 3: Last Used Style:** If no style is in the query and no *Default Style* is set, the agent uses the *Last Used Style*.
        * **Priority 4 (Fallback):** If none of the above are available (e.g., a new user), the agent **must ask the user** (in Conversational Mode) or **fail** (in Direct Command Mode).
    3.  The agent must provide a way for the user to set or change their *Default Style* (e.g., via a command like "Set my default style to BNR").

* **File Type Selection Logic:**

    1.  The agent must manage two persistent memory concepts: a **Default Format** (long-term preference) and a **Last Used Format** (most recent).
    2.  When a user requests a chart, the agent **must** follow this priority order to determine which file format (PNG or SVG) to generate:
        * **Priority 1: Format in Query:** If the user specifies a format in the current prompt (e.g., "...as an SVG" or "...save as PNG"), that format is used. This choice also updates the *Last Used Format* in memory.
        * **Priority 2: Default Format:** If no format is in the query, the agent checks if the user has a *Default Format* saved. If yes, that format is used.
        * **Priority 3: Last Used Format:** If no format is in the query and no *Default Format* is set, the agent uses the *Last Used Format*.
        * **Priority 4 (Fallback):** If none of the above are available (e.g., a new user), the agent **must default to PNG**.

### 4.3. Brand Guidelines (Colors)

The agent **must** use these exact color palettes for the charts.

```json
{
  "colors-fd": {
    "primary": "#379596",
    "content": "#191919",
    "background": "#ffeadb"
  },
  "colors-bnr": {
    "primary": "#ffd200",
    "content": "#000",
    "background": "#fff"
  }
}