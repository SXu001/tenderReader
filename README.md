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

## Roadmap

*   **v0.5:** Generate human-friendly markdown/text reports alongside the raw JSON output.
*   **v1.0:** Introduce Step 3: Automatically transform `extracted_data.json` into a structured pitch-deck outline that you can feed directly into Claude, NotebookLM, or presentation tools.
