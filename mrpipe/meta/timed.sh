#!/usr/bin/env bash

# Usage: timed_wrapper.sh <command> <args...>

cmd=("$@")
tmp=$(mktemp)

# Record start time
start=$(date +%s.%N)

# Run the command normally, capturing ONLY /usr/bin/time output
/usr/bin/time -v -o "$tmp" "$@"

# Record end time
end=$(date +%s.%N)

# Extract fields
user=$(grep "User time" "$tmp" | awk -F': ' '{print $2}')
sys=$(grep "System time" "$tmp" | awk -F': ' '{print $2}')
maxrss=$(grep "Maximum resident set size" "$tmp" | awk -F': ' '{print $2}')

rm "$tmp"

# Convert KB → GB
maxrss_gb=$(echo "scale=3; $maxrss / (1024*1024)" | bc)

# Compute real time
real=$(echo "$end - $start" | bc)

# Summary
echo ""
echo "----------------------------------------"
echo " Command: $*"
echo "----------------------------------------"
echo " Real time : ${real}s"
echo " User time : ${user}s"
echo " Sys time  : ${sys}s"
echo " Max RSS   : ${maxrss_gb} GB"
echo "----------------------------------------"
