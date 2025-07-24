#!/usr/bin/env python3

import json
import sys

def add_name_value_pair(file_path, name, value):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        data[name] = value

        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

        print(f'Successfully added "{name}: {value}" to {file_path}')
    except FileNotFoundError:
        print(f'File {file_path} not found.')
    except json.JSONDecodeError:
        print(f'Error decoding JSON in {file_path}.')
    except Exception as e:
        print(f'An error occurred: {e}')


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: ./add_entry.py <file_path> <key> <value>")
        sys.exit(1)

    file_path = sys.argv[1]
    key = sys.argv[2]
    value = sys.argv[3]

    add_name_value_pair(file_path, key, value)
