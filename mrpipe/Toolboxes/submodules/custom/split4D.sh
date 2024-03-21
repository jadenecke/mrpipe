#!/bin/bash


# Check if the correct number of arguments are provided
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <inputfile> <stem> [<outputfile1> <outputfile2> ...]"
  exit 1
fi

# Get the input file, stem and the output files
inputfile=$1
stem=$2
shift 2
outputfiles=("$@")


# Call the function to split the file
fslsplit "$inputfile" "$stem" -t

# Rename the output files if they are provided
if [ "${#outputfiles[@]}" -gt 0 ]; then
  for i in "${!outputfiles[@]}"; do
    mv "${stem}$(printf "%04d" $((i))).nii.gz" "${outputfiles[$i]}"
  done
fi