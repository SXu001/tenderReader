import os
import json
import re
import yaml
from typing import List, Dict, Any
from pathlib import Path
import pdfplumber
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
import pandas as pd
from ollama import Client as OllamaClient
from openai import OpenAI
from dotenv import load_dotenv

class TenderPipeline:
    def __init__(self, 
                 input_dir_name: str = "TenderFiles", 
                 intermediate_dir_name: str = "processed_tenders", 
                 output_dir_name: str = "extracted_data",
                 config_name: str = "soul.yaml",
                 env_name: str = "reader.env"):
        
        # Determine base directory from script file path
        self.script_dir = Path(__file__).parent.resolve()
        
        # Setup paths relative to the script location
        self.input_dir = self.script_dir / input_dir_name
        self.intermediate_dir = self.script_dir / intermediate_dir_name
        self.output_dir = self.script_dir / output_dir_name
        self.config_path = self.script_dir / config_name
        self.env_path = self.script_dir / env_name
        
        # Create necessary directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load environment variables
        if self.env_path.exists():
            load_dotenv(dotenv_path=self.env_path)
        else:
            print(f"⚠️ Warning: Environment file not found at {self.env_path}")

        # Initialize Models & Clients
        self.EXTRACTOR_MODEL = 'qwen2.5:7b'    # Fast, lightweight (LOCAL)
        self.REASONING_MODEL = 'deepseek-v4-pro' # Heavy thinker (ONLINE API)
        
        self.client_ollama = OllamaClient(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'))
        self.client_deepseek = OpenAI(
            base_url=os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
            api_key=os.getenv("DEEPSEEK_API_KEY")
        )

    def clean_text(self, text: str) -> str:
        """Removes excessive whitespace and noisy repetitive header/footer remnants."""
        if not text:
            return ""
        text = re.sub(r'(Page\s+\d+\s+of\s+\d+|页码：\s*\d+\s*/\s*\d+)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)  
        return text.strip()

    def detect_language(self, text: str) -> str:
        """Simple heuristic to detect if a chunk is predominantly Chinese or English."""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        return "zh" if chinese_chars > (len(text) * 0.1) else "en"

    def process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Extracts text and preserves tables explicitly via pdfplumber."""
        document_structure = {
            "document_metadata": {"file_name": file_path.name, "source_type": "pdf"},
            "chunks": []
        }
        
        chunk_counter = 1
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                page_text = page.extract_text() or ""
                
                markdown_tables = []
                if tables:
                    for table in tables:
                        cleaned_table = [[str(cell or '').strip() for cell in row] for row in table if any(row)]
                        if cleaned_table and len(cleaned_table) > 1:
                            df = pd.DataFrame(cleaned_table[1:], columns=cleaned_table[0])
                            markdown_tables.append(df.to_markdown(index=False))

                cleaned_text = self.clean_text(page_text)
                if not cleaned_text and not markdown_tables:
                    continue

                if cleaned_text:
                    document_structure["chunks"].append({
                        "chunk_id": f"chunk_{chunk_counter:03d}",
                        "heading_hierarchy": [f"Page {page_num}"],
                        "content_type": "text",
                        "language": self.detect_language(cleaned_text),
                        "text_content": cleaned_text
                    })
                    chunk_counter += 1

                for md_table in markdown_tables:
                    document_structure["chunks"].append({
                        "chunk_id": f"chunk_{chunk_counter:03d}",
                        "heading_hierarchy": [f"Page {page_num}", "Table Data"],
                        "content_type": "table",
                        "language": self.detect_language(md_table),
                        "text_content": md_table
                    })
                    chunk_counter += 1

        return document_structure

    def process_docx(self, file_path: Path) -> Dict[str, Any]:
        """Extracts text paragraphs and inline tables sequentially from Word documents."""
        doc = Document(file_path)
        document_structure = {
            "document_metadata": {"file_name": file_path.name, "source_type": "docx"},
            "chunks": []
        }
        
        chunk_counter = 1
        current_heading = "General"
        
        for element in doc.element.body:
            if element.tag.endswith('p'):  
                p = Paragraph(element, doc)
                text = p.text.strip()
                if not text:
                    continue
                
                style_name = p.style.name if (p.style and hasattr(p.style, 'name') and p.style.name) else ""
                if style_name.startswith('Heading'):
                    current_heading = text
                    
                cleaned_text = self.clean_text(text)
                if cleaned_text:
                    document_structure["chunks"].append({
                        "chunk_id": f"chunk_{chunk_counter:03d}",
                        "heading_hierarchy": [current_heading],
                        "content_type": "text",
                        "language": self.detect_language(cleaned_text),
                        "text_content": cleaned_text
                    })
                    chunk_counter += 1
                    
            elif element.tag.endswith('tbl'):  
                t = Table(element, doc)
                data = []
                for row in t.rows:
                    data.append([cell.text.strip() for cell in row.cells])
                
                if data and len(data) > 1:
                    headers = data[0]
                    rows = data[1:]
                    
                    max_cols = len(headers)
                    padded_rows = [row + [''] * (max_cols - len(row)) if len(row) < max_cols else row[:max_cols] for row in rows]
                    
                    df = pd.DataFrame(padded_rows, columns=headers)
                    md_table = df.to_markdown(index=False)
                    
                    document_structure["chunks"].append({
                        "chunk_id": f"chunk_{chunk_counter:03d}",
                        "heading_hierarchy": [current_heading, "Table Data"],
                        "content_type": "table",
                        "language": self.detect_language(md_table),
                        "text_content": md_table
                    })
                    chunk_counter += 1

        return document_structure

    def process_xlsx(self, file_path: Path) -> Dict[str, Any]:
        """Converts multi-sheet pricing/requirement Excel workbooks into chunked Markdown strings."""
        document_structure = {
            "document_metadata": {"file_name": file_path.name, "source_type": "xlsx"},
            "chunks": []
        }
        
        xl = pd.ExcelFile(file_path)
        chunk_counter = 1
        
        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            if df.empty:
                continue
                
            md_table = df.to_markdown(index=False)
            document_structure["chunks"].append({
                "chunk_id": f"chunk_{chunk_counter:03d}",
                "heading_hierarchy": [f"Sheet: {sheet_name}"],
                "content_type": "table",
                "language": self.detect_language(md_table),
                "text_content": md_table
            })
            chunk_counter += 1
            
        return document_structure

    def load_prompt_config(self) -> Dict[str, Any]:
        """Loads prompt configs from soul.yaml."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"❌ Configuration file 'soul.yaml' is missing at {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def execute_pipeline(self):
        """Main pipeline orchestration method."""
        supported_extensions = {'.pdf', '.docx', '.xlsx', '.xls'}
        
        try:
            files = [f for f in self.input_dir.iterdir() if f.suffix.lower() in supported_extensions]
        except Exception as e:
            print(f"Error reading directory {self.input_dir}: {e}")
            return

        if not files:
            print(f"No valid tender documents found in: {self.input_dir}\nPlease place your source files there.")
            return

        # Load Prompt Profiles
        try:
            prompt_config = self.load_prompt_config()
        except Exception as e:
            print(e)
            return

        # Formatting configurations for Phase 2 & 3
        target_points = "\n".join([f"- {point}" for point in prompt_config.get('extraction_points', [])])
        toDoWhat = "\n".join([f"- {point}" for point in prompt_config.get('instructions', [])])
        
        role_data = prompt_config.get('role', [])
        youAre = "\n".join([f"- {point}" for point in role_data]) if isinstance(role_data, list) else str(role_data)
        
        analysisInstructions = "\n".join([f"- {point}" for point in prompt_config.get('analysis_instructions', [])])

        print(f"Found {len(files)} file(s) to process.\n" + "="*40)

        for file_path in files:
            print(f"\n--- Processing: {file_path.name} ---")
            ext = file_path.suffix.lower()
            
            # ==========================================
            # STAGE 1: Parse Files to JSON Chunks
            # ==========================================
            print(f"Stage 1: Parsing file contents...")
            if ext == '.pdf':
                parsed_data = self.process_pdf(file_path)
            elif ext == '.docx':
                parsed_data = self.process_docx(file_path)
            elif ext in ['.xlsx', '.xls']:
                parsed_data = self.process_xlsx(file_path)
            else:
                continue

            # Determine dominant language
            all_langs = [c["language"] for c in parsed_data["chunks"]]
            parsed_data["document_metadata"]["primary_language"] = max(set(all_langs), key=all_langs.count) if all_langs else "en"

            # Save the intermediate clean JSON chunk file
            intermediate_file = self.intermediate_dir / f"{file_path.stem}.json"
            with open(intermediate_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=2)
            print(f" Saved intermediate JSON structure to: {intermediate_file.name}")

            # Collect raw text content for the LLM context
            document_text = "\n".join([chunk["text_content"] for chunk in parsed_data["chunks"] if chunk.get("text_content")])
            
            if not document_text.strip():
                print(f"⚠️ No clean text content extracted from {file_path.name}. Skipping analysis.")
                continue

            # ==========================================
            # STAGE 2: Condense Context via LOCAL LLM
            # ==========================================
            print(f"Stage 2: Condensing with local {self.EXTRACTOR_MODEL}...")
            stage1_prompt = f"""
            {youAre}
            {toDoWhat}
            {target_points}
            
            Discard all other irrelevant text, introductions, and boilerplate terminology.
            
            Document:
            {document_text}
            """
            
            try:
                response_stage1 = self.client_ollama.generate(
                    model=self.EXTRACTOR_MODEL,
                    prompt=stage1_prompt,
                    options={'num_ctx': 32786, 'num_predict': 4096, 'temperature': 0.0}
                )
                condensed_context = response_stage1['response']
                print("Success! Condensed context excerpt:", condensed_context[:300].replace('\n', ' '))
            except Exception as e:
                print(f"❌ Local Ollama inference failed: {e}")
                continue

            # ==========================================
            # STAGE 3: Deep DeepSeek Analysis (ONLINE API)
            # ==========================================
            print(f"Stage 3: Extracting structure with online {self.REASONING_MODEL}...")
            stage2_prompt = f"""
            {youAre}
            Only analysis the Condensed Document given below. The following document could be in English, Chinese, or both. 
            Given information related to the following points. Give only the requested facts accurately. Do not extrapolate or guess. If a piece of information is missing, state 'Not Specified'.
            {analysisInstructions}
            
            Condensed Document Text:
            {condensed_context}
            
            IMPORTANT: Output ONLY valid JSON, no markdown, no explanations, no extra text.
            """
            
            try:
                response_stage2 = self.client_deepseek.chat.completions.create(
                    model=self.REASONING_MODEL,
                    messages=[{"role": "user", "content": stage2_prompt}],
                    temperature=0.0,
                    max_tokens=4096,
                    response_format={"type": "json_object"}
                )
                raw_output = response_stage2.choices[0].message.content
                
                # Dynamic JSON block isolation regex
                json_match = re.search(r'(\{.*\}).*', raw_output, re.DOTALL)
                json_string = json_match.group(1) if json_match else raw_output
                
                final_data = json.loads(json_string)
                final_data['source_file'] = file_path.name
                
                # Save Final Data
                output_file = self.output_dir / f"extracted_{file_path.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    json.dump(final_data, out_f, indent=4, ensure_ascii=False)
                
                print(f"💾 Success! Saved structured data analysis to: {output_file.name}")

            except Exception as e:
                print(f"❌ Failed parsing final JSON from LLM: {str(e)}")
                error_log = self.output_dir / f"error_{file_path.stem}.txt"
                with open(error_log, 'w', encoding='utf-8') as err_f:
                    err_f.write(raw_output)
                print(f"⚠️ Raw AI response saved to {error_log.name} for inspection.")
                
        print("\n" + "="*40 + "\nAll file parsing and analysis pipelines complete.")

if __name__ == "__main__":
    # Initialize and execute end-to-end
    pipeline = TenderPipeline()
    pipeline.execute_pipeline()