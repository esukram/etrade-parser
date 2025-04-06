# E-Trade PDF Parser

A Python tool for parsing PDF documents using OpenAI's GPT-4o-mini model to extract structured data according to a defined JSON schema. Includes conversion utilities to transform the extracted JSON data into CSV format for easier analysis.

## Installation

```bash
# Clone the repository
git clone https://github.com/esukram/etrade-parser.git
cd etrade-parser

# Set up Python virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project directory with your OpenAI API key and optional base URL:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # Optional: only needed for custom deployments
```

Alternatively, you can provide these values as command-line arguments.

## Usage

```bash
# Process a single PDF file
python parser.py path/to/document.pdf --schema path/to/schema.json [--output output.json]

# Process all PDFs in a directory (non-recursive)
python parser.py path/to/directory --schema path/to/schema.json [--output output.json]

# Process all PDFs in a directory recursively
python parser.py path/to/directory --schema path/to/schema.json --recursive [--output output.json]

# Pretty print the JSON output
python parser.py path/to/document.pdf --schema path/to/schema.json --pretty
```

### Arguments

- `path`: Path to a PDF file or directory containing PDFs
- `--schema`: Path to the JSON schema file defining the structure of the output
- `--output`: (Optional) Path to save the JSON output (results are always printed to stdout)
- `--recursive`, `-r`: (Optional) Recursively search for PDFs in subdirectories
- `--max-workers`: (Optional) Maximum number of concurrent PDF processing tasks (default: 4)
- `--pretty`: (Optional) Pretty print the JSON output
- `--api-key`: (Optional) OpenAI API key (can also be set via OPENAI_API_KEY environment variable)
- `--api-base`: (Optional) OpenAI API base URL (can also be set via OPENAI_API_BASE environment variable)

### Example Schema

Create a JSON file that defines the structure of the data you want to extract:

```json
{
  "type": "object",
  "properties": {
    "transactionDate": {
      "type": "string",
      "description": "Date of the transaction"
    },
    "accountNumber": {
      "type": "string",
      "description": "Account number associated with the transaction"
    },
    "transactions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "date": { "type": "string" },
          "description": { "type": "string" },
          "amount": { "type": "number" },
          "type": { "type": "string" }
        }
      }
    }
  }
}
```

## Example Usage

```bash
# Parse a statement PDF using a schema and save the output
python parser.py statements/march_2023.pdf --schema schemas/statement_schema.json --output parsed_statement.json
# Recursively parse all PDFs in a directory with ignore directory
python parser.py --schema default_schema.json --recursive --ignore-dirs sell -- ${home}/shares/2024/

# Convert JSON output to CSV
python convert.py parsed_output.json --output parsed_output.csv

# Print the flattened structure for the first record
python convert.py parsed_output.json --pretty
```

## JSON Conversion Utilities

After parsing PDFs into structured JSON data, you can convert the results to CSV or Excel format:

```bash
# Convert to CSV (default)
python convert.py path/to/input.json [--output path/to/output.csv] [--headers field1 field2 ...] [--pretty]

# Convert to Excel
python convert.py path/to/input.json --to-xlsx [--output path/to/output.xlsx] [--headers field1 field2 ...] [--pretty]
```

### Conversion Arguments

- `json_file`: Path to the JSON file to convert
- `--output`, `-o`: (Optional) Path for the output file (defaults to input filename with appropriate extension)
- `--headers`: (Optional) Specific headers to include in the output file
- `--pretty`: (Optional) Print the flattened structure of the first record to understand available fields
- `--to-csv`: (Optional) Convert to CSV format (default behavior)
- `--to-xlsx`: (Optional) Convert to Excel format (.xlsx)
