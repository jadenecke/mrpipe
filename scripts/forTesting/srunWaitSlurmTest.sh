#!/usr/bin/env bash

# How many srun tasks you want running at once
MAX_PARALLEL="2"

launch() {
    echo "Launching: $@"
    $@ &
    while [ `jobs | wc -l` -ge $MAX_PARALLEL ]
    do
        sleep 2
    done
}

# -------------------------
# Your thousand srun calls:
# -------------------------

launch sleep 5
launch sleep 5
launch sleep 5
launch sleep 5
launch sleep 5
launch sleep 5
launch sleep 5
# ...
# ...
# 1000 more launch calls
# ...
# ...

# Wait for all remaining tasks
wait

