# tenderReader

# Tender Summary & Risk Analysis Tool

A lightweight, cost-effective tool designed for **technology and solution consultants** to rapidly assess complex tender documents upon first encounter. 

Instead of spending hours reading through hundreds of pages, this tool uses a hybrid AI approach to extract key technical requirements, business constraints, and risk factors—while minimizing token costs and eliminating AI hallucinations.

---

## The Problem
Tender documents for complex technology or transformation projects often span hundreds of pages scattered across multiple files. Only a fraction of this information is critical for a consultant to make an initial **go/no-go decision** or to prepare a pitch deck for a first client meeting. 

While you can feed these massive documents into a commercial LLM, it is often incredibly expensive in token consumption. Furthermore, relying entirely on a public LLM risks **AI hallucinations** that are difficult to spot without reading the raw documents yourself.

## How It Works
This project uses a dual-stage pipeline to process documents safely and efficiently:

1. **Local Processing (Data Reduction):** A small, locally deployed model reads the raw tender documents. It filters out the noise and extracts only the relevant text word-for-word, outputting a structured `processed_tender.json`. This keeps sensitive data local and drastically cuts down the token footprint.
2. **Cloud Extraction (Insights):** The condensed JSON file is fed to a powerful LLM (currently utilizing DeepSeek via Ollama) to synthesize the data and generate the final structured output (`extracted_data.json`).

---

## Structured Output Schema
The tool outputs a structured JSON file containing the following fields. Any missing information in the source documents explicitly returns `null`.

*   `tender_title`: Name of the tender.
*   `buyer`: The issuing organization or client.
*   `submission_deadline`: The final date for proposal submission.
*   `as_is_technology_stack`: The client's current technical infrastructure.
*   `technical_requirements`: Core technical deliverables and constraints.
*   `business_requirements`: Commercial, operational, and compliance needs.
*   `requirement_analysis`: An evaluation of the complexity of the requirements.
*   `evaluation_criteria`: How the winning bid will be selected.
*   `contract_value`: Budget or estimated financial value of the contract.
*   `key_dates`: Project milestones, Q&A deadlines, and interview dates.
*   `summary`: A strict, 5-sentence executive summary written from the bidder's perspective covering:
    1. Who is buying what.
    2. What kind of provider they are looking for.
    3. Summary of technical requirements.
    4. Summary of business requirements.
    5. High-level potential risks.

---

## Installation & Setup

### 1. Prerequisites
* Ensure you have **Python 3.8+** installed on your system. 
* You will also need a local installation of [Ollama](https://ollama.com/) running the `qwen2.5:7b` model.

### 2. Install Required Libraries
Run the following command to install all the necessary dependencies for document parsing, data manipulation, and LLM orchestration:

```bash
pip install pdfplumber python-docx pandas tabulate ollama openai python-dotenv pyyaml
```
### 3. Environment Configuration
Create a file named reader.env in the root directory of the project and add the following lines:

```bash
DEEPSEEK_API_KEY=your_actual_deepseek_api_key_here
OLLAMA_HOST=http://localhost:11434
DEEPSEEK_BASE_URL=[https://api.deepseek.com](https://api.deepseek.com)
```

---

## Roadmap

*   **v0.5:** Generate human-friendly markdown/text reports alongside the raw JSON output.
*   **v1.0:** Introduce Step 3: Automatically transform `extracted_data.json` into a structured pitch-deck outline that you can feed directly into Claude, NotebookLM, or presentation tools.
