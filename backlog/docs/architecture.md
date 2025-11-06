# Architecture Document: Graph Agent (MVP)

**Version:** 1.2 (Final)
**Author:** Architect

## 1. Overview & Guiding Principles

This document outlines the architecture for the **Graph Agent**, a CLI tool for journalists to create brand-compliant charts from data.

* **Guiding Principle:** A clean, modular "Agentic" architecture. The core logic (the "brain") is decoupled from the specific tools (parsing, charting) and the interface (CLI).
* **Core Technology:** The system is a **Python** application built using **LangGraph** as the central orchestrator, **Gemini** as the reasoning LLM, and **`click`** as the CLI framework.

---

## 2. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Orchestration** | **LangGraph** | A state machine (graph) is perfect for managing the complex, stateful logic of "Conversational" vs. "Direct" modes and the multi-step tool use. |
| **Language Model** | **Google Gemini** | Provides the core intelligence for NLU (EN/NL), data extraction from text, and the reasoning required to use the data tools. |
| **CLI Framework** | **`click`** | A simple, powerful library for creating the dual-mode (conversational REPL vs. direct command) CLI with its override flags. |
| **Chart Generation** | **`matplotlib`** | A robust, industry-standard library that provides full control over styling (for brand compliance) and supports both **SVG** and **PNG** output. |
| **Excel Parsing** | **`pandas`** | The standard for Excel I/O and data manipulation. Used by all data extraction tools. |
| **Package Mgmt** | **`uv`** | A fast, modern Python package manager and virtual environment wrapper. |
| **Config Storage** | **`JSON` file** | A simple, human-readable file (`~/.config/graph-agent/settings.json`) for persistent user preferences (style, format). |

---

## 3. Component Architecture

The system is comprised of four primary components: **Interface**, **Agent Core**, **Tools**, and **Configuration**.

[Image of a component diagram showing CLI, Agent Core (LangGraph), Tools (Matplotlib, Pandas), and Config (JSON)]

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
* **Logic:** Gathers all arguments and invokes the Agent Core in a single, stateless run. The agent will be instructed to **prioritize