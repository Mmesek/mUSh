#!/bin/bash

directory="songs"

find "$directory" -type f | while read -r file; do
    echo "Processing file: $file"
    echo "Result: \"$file\""
    python -m mUSh -filepath="$file"
done