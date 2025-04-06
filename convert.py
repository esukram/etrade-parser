#!/usr/bin/env python3
"""
Convert JSON output from PDF parser to CSV or Excel format.
Takes the JSON output from parser.py and creates a CSV or Excel file.
"""
import json
import csv
import sys
import argparse
import os
from typing import Dict, Any, List, Optional
import pandas as pd


def flatten_json(nested_json: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
    """
    Flatten nested JSON structure into a flat dictionary with keys joined by dots.
    e.g. {'a': {'b': 1}} becomes {'a.b': 1}
    """
    flattened = {}
    
    for key, value in nested_json.items():
        new_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            # Recursively flatten nested dictionaries
            nested_flat = flatten_json(value, new_key)
            flattened.update(nested_flat)
        else:
            # Add leaf values to the flattened dictionary
            flattened[new_key] = value
            
    return flattened


def prepare_flattened_data(json_data: List[Dict[str, Any]], headers: Optional[List[str]] = None):
    """
    Prepare flattened data from JSON objects, with optional header filtering.
    Returns flattened data and headers.
    """
    if not json_data:
        print("No data to convert", file=sys.stderr)
        return [], []
    
    # Flatten all JSON objects
    flattened_data = [flatten_json(item) for item in json_data]
    
    # Determine headers - either use provided headers or collect all unique keys
    if not headers:
        # Get all unique keys from all flattened records
        all_headers = set()
        for item in flattened_data:
            all_headers.update(item.keys())
        headers = sorted(list(all_headers))
    
    return flattened_data, headers


def convert_to_csv(flattened_data: List[Dict[str, Any]], output_path: str, headers: List[str]):
    """
    Convert flattened data to CSV format and write to file.
    """
    # Write to CSV
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for item in flattened_data:
            # Fill in missing keys with empty strings
            row = {header: item.get(header, '') for header in headers}
            writer.writerow(row)


def convert_to_excel(flattened_data: List[Dict[str, Any]], output_path: str, headers: List[str]):
    """
    Convert flattened data to Excel format and write to file.
    """
    # Create DataFrame from flattened data with specified headers
    df_data = []
    for item in flattened_data:
        row_data = {header: item.get(header, '') for header in headers}
        df_data.append(row_data)
    
    df = pd.DataFrame(df_data)
    
    # Write to Excel file
    df.to_excel(output_path, index=False)


def main():
    """Main function to handle command line arguments and convert JSON to CSV or Excel."""
    parser = argparse.ArgumentParser(description="Convert JSON output from PDF parser to CSV or Excel format")
    parser.add_argument("json_file", help="Path to the JSON file to convert")
    parser.add_argument("--output", "-o", help="Path for the output file (defaults to input filename with appropriate extension)")
    parser.add_argument("--headers", nargs="+", help="Specific headers to include in the output file (optional)")
    parser.add_argument("--pretty", action="store_true", help="Print flattened structure to stdout")
    
    # Output format options group
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument("--to-csv", action="store_true", help="Convert to CSV format (default)")
    format_group.add_argument("--to-xlsx", action="store_true", help="Convert to Excel format")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found.", file=sys.stderr)
        return 1
    
    # Determine output format - default to CSV if none specified
    output_format = "xlsx" if args.to_xlsx else "csv"
    
    # Set output filename if not provided
    output_path = args.output
    if not output_path:
        base_name = os.path.splitext(args.json_file)[0]
        output_path = f"{base_name}.{output_format}"
    
    # Load JSON data
    try:
        with open(args.json_file, 'r') as f:
            json_data = json.load(f)
            
            # Check if JSON is an array or a single object
            if not isinstance(json_data, list):
                json_data = [json_data]
    except json.JSONDecodeError:
        print(f"Error: '{args.json_file}' contains invalid JSON.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading JSON file: {e}", file=sys.stderr)
        return 1
    
    # Convert and save to the appropriate format
    try:
        # Prepare flattened data
        flattened_data, headers = prepare_flattened_data(json_data, args.headers)
        
        if len(flattened_data) == 0:
            print("No data to convert", file=sys.stderr)
            return 1
            
        # Sort data by releaseSummary.releaseDate if it exists
        flattened_data = sorted(
            flattened_data,
            key=lambda x: x.get('releaseSummary.releaseDate', ''),
        )
            
        # Convert to the appropriate format
        if args.to_xlsx:
            convert_to_excel(flattened_data, output_path, headers)
        else:
            convert_to_csv(flattened_data, output_path, headers)
            
        print(f"Successfully converted {args.json_file} to {output_path}", file=sys.stderr)
        
        # If --pretty flag is set, print the flattened structure of the first item
        if args.pretty and json_data:
            print("\nFlattened structure (first record):", file=sys.stderr)
            flattened = flatten_json(json_data[0])
            for key, value in sorted(flattened.items()):
                print(f"{key}: {value}", file=sys.stderr)
        
        return 0
    except Exception as e:
        print(f"Error converting file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())