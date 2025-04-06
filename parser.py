#!/usr/bin/env python3
"""
PDF Parser that utilizes the OpenAI API with the GPT-4o-mini model to extract structured data.
"""
import os
import sys
import json
import argparse
import pathlib
import logging
from typing import Dict, Any, Optional, List
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress the specific warning about CropBox
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# Load environment variables from .env file
load_dotenv()

class PDFParser:
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """Initialize the PDF parser with OpenAI API key and optional base URL."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Provide it as an argument or set OPENAI_API_KEY environment variable.")
        
        # Get API base URL from environment or use default
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        
        # Initialize OpenAI client with appropriate parameters
        client_kwargs = {"api_key": self.api_key}
        if self.api_base:
            client_kwargs["base_url"] = self.api_base
            
        self.client = OpenAI(**client_kwargs)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from a PDF file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        text_content = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text_content += page.extract_text() or ""
                    text_content += "\n\n"
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {e}")
        
        return text_content.strip()
    
    def parse_pdf(self, pdf_path: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse PDF content according to the provided schema using OpenAI."""
        # Extract text from PDF
        text_content = self.extract_text_from_pdf(pdf_path)
        
        # Prepare the prompt with schema information
        schema_str = json.dumps(schema, indent=2)
        
        prompt = f"""
        Extract information from the following document text according to this JSON schema:
        
        {schema_str}
        
        Return ONLY a valid JSON object matching the schema. Do not include any explanations, notes, or text outside of the JSON object.
        
        Document text:
        {text_content}
        """
        
        # Call OpenAI API
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a document parsing assistant that extracts structured data from text. Always return valid JSON according to the specified schema."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # Use deterministic output
            )
            
            result_text = response.choices[0].message.content
            
            # Extract JSON from the response
            try:
                # Try to find and parse JSON in the response
                result_json = json.loads(result_text)
                return result_json
            except json.JSONDecodeError:
                # If the model didn't return clean JSON, try to extract it
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    try:
                        result_json = json.loads(json_match.group(0))
                        return result_json
                    except:
                        raise ValueError("Failed to extract valid JSON from the model response")
                else:
                    raise ValueError("Model response did not contain valid JSON")
                
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {e}")

def find_pdf_files(directory: str, ignore_dirs: List[str] = None) -> List[str]:
    """Find all PDF files in a directory recursively, optionally ignoring specified directories."""
    pdf_files = []
    ignore_dirs = ignore_dirs or []
    
    directory_path = pathlib.Path(directory)
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if directory_path.is_file() and directory_path.suffix.lower() == '.pdf':
        return [str(directory_path)]
    
    for path in directory_path.glob('**/*.pdf'):
        # Check if any parent directory should be ignored
        if not any(ignore_dir in path.parts for ignore_dir in ignore_dirs):
            pdf_files.append(str(path))
    
    return sorted(pdf_files)

def process_pdf(pdf_path: str, schema: Dict[str, Any], pdf_parser: PDFParser) -> Dict[str, Any]:
    """Process a single PDF file and return the results."""
    try:
        # Get the filename to include in the result
        pdf_filename = os.path.basename(pdf_path)
        
        # Parse the PDF
        result = pdf_parser.parse_pdf(pdf_path, schema)
        
        # Add the source filename to the result
        result["source_file"] = pdf_filename
        
        return {
            "path": pdf_path,
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "path": pdf_path,
            "success": False,
            "error": str(e)
        }

def main():
    """Command line interface for the PDF parser."""
    parser = argparse.ArgumentParser(description="Parse PDF documents using OpenAI's GPT-4o-mini model")
    parser.add_argument("path", help="Path to a PDF file or directory containing PDFs")
    parser.add_argument("--schema", required=True, help="Path to JSON schema file")
    parser.add_argument("--output", help="Path to save the output JSON (optional, results always go to stdout)")
    parser.add_argument("--api-key", help="OpenAI API key (can also be set via OPENAI_API_KEY environment variable)")
    parser.add_argument("--api-base", help="OpenAI API base URL (can also be set via OPENAI_API_BASE environment variable)")
    parser.add_argument("--recursive", "-r", action="store_true", help="Recursively search for PDFs in directories")
    parser.add_argument("--ignore-dirs", nargs="+", default=[], help="Directories to ignore when recursively searching (e.g., --ignore-dirs sell archive temp)")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum number of concurrent PDF processing tasks")
    parser.add_argument("--pretty", action="store_true", help="Pretty print the JSON output")
    
    args = parser.parse_args()
    
    # Load schema from file
    try:
        with open(args.schema, 'r') as f:
            schema = json.load(f)
            
        # Ensure schema includes source_file property if it's an object
        if schema.get("type") == "object" and "properties" in schema:
            if "source_file" not in schema["properties"]:
                schema["properties"]["source_file"] = {
                    "type": "string",
                    "description": "Source PDF filename"
                }
    except Exception as e:
        print(f"Error loading schema file: {e}", file=sys.stderr)
        return 1
    
    # Find PDF files to process
    try:
        if args.recursive:
            pdf_files = find_pdf_files(args.path, ignore_dirs=args.ignore_dirs)
        else:
            # Single file mode
            if os.path.isfile(args.path) and args.path.lower().endswith('.pdf'):
                pdf_files = [args.path]
            else:
                # Non-recursive directory mode
                pdf_files = [f for f in pathlib.Path(args.path).glob('*.pdf')]
                pdf_files = [str(path) for path in pdf_files]
        
        if not pdf_files:
            print(f"No PDF files found in path: {args.path}", file=sys.stderr)
            return 1
        
        # Initialize parser
        pdf_parser = PDFParser(api_key=args.api_key, api_base=args.api_base)
        
        # Process the PDFs
        all_results = []
        
        # Status messages to stderr
        if len(pdf_files) > 1:
            print(f"Processing {len(pdf_files)} PDF files...", file=sys.stderr)
        
        if len(pdf_files) == 1:
            # For single file, process directly
            pdf_path = pdf_files[0]
            try:
                pdf_filename = os.path.basename(pdf_path)
                result = pdf_parser.parse_pdf(pdf_path, schema)
                result["source_file"] = pdf_filename
                all_results.append(result)
                print(f"Successfully processed: {pdf_path}", file=sys.stderr)
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}", file=sys.stderr)
                return 1
        else:
            # For multiple files, use parallel processing
            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {executor.submit(process_pdf, pdf_path, schema, pdf_parser): 
                           pdf_path for pdf_path in pdf_files}
                
                for future in as_completed(futures):
                    pdf_path = futures[future]
                    try:
                        result = future.result()
                        if result["success"]:
                            all_results.append(result["result"])
                            print(f"Successfully processed: {pdf_path}", file=sys.stderr)
                        else:
                            print(f"Failed to process {pdf_path}: {result['error']}", file=sys.stderr)
                    except Exception as e:
                        print(f"Error processing {pdf_path}: {e}", file=sys.stderr)
        
        # Output results to stdout
        output_json = all_results
        
        # Determine indentation based on pretty printing flag
        indent = 2 if args.pretty else None
        print(json.dumps(output_json, indent=indent))
        
        # Additionally save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_json, f, indent=2)
            print(f"Results also saved to {args.output}", file=sys.stderr)
            
        return 0
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())