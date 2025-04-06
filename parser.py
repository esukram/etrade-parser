#!/usr/bin/env python3
"""
PDF Parser that utilizes the OpenAI API with the GPT-4o-mini model to extract structured data.
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, Optional
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

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

def main():
    """Command line interface for the PDF parser."""
    parser = argparse.ArgumentParser(description="Parse PDF documents using OpenAI's GPT-4o-mini model")
    parser.add_argument("pdf_path", help="Path to the PDF file to parse")
    parser.add_argument("--schema", required=True, help="Path to JSON schema file")
    parser.add_argument("--output", help="Path to save the output JSON (default: stdout)")
    parser.add_argument("--api-key", help="OpenAI API key (can also be set via OPENAI_API_KEY environment variable)")
    parser.add_argument("--api-base", help="OpenAI API base URL (can also be set via OPENAI_API_BASE environment variable)")
    
    args = parser.parse_args()
    
    # Load schema from file
    try:
        with open(args.schema, 'r') as f:
            schema = json.load(f)
    except Exception as e:
        print(f"Error loading schema file: {e}")
        return
    
    try:
        # Initialize parser and parse PDF
        pdf_parser = PDFParser(api_key=args.api_key, api_base=args.api_base)
        result = pdf_parser.parse_pdf(args.pdf_path, schema)
        
        # Always output result to stdout
        print(json.dumps(result, indent=2))
        
        # Additionally save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results also saved to {args.output}", file=sys.stderr)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()