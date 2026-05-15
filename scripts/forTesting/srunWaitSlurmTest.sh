#!/usr/bin/env bash

# How many srun tasks you want running at once
MAX_PARALLEL="2"

launch() {
    echo "Launching: $@"
    "$@" &
    jobs -r
    echo "Current number of running jobs: `jobs -r | wc -l`"
    while [ `jobs -r | wc -l` -ge $MAX_PARALLEL ]
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

