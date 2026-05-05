#!/usr/bin/env bash

# Usage: timed_wrapper.sh <dbpath> <db> <hash> <command> <args...>

dbpath="$1"
db="$2"
dbhash="$3"
shift 3
cmd=("$@")
tmp=$(mktemp)
stdout_log=$(mktemp)
stderr_log=$(mktemp)

# Record start time
start=$(date +%s.%N)

# Run the command normally, capturing ONLY /usr/bin/time output
/usr/bin/time -v -o "$tmp" "${cmd[@]}" > >(tee "$stdout_log") 2> >(tee "$stderr_log" >&2)
errorstatus=$?

# Record end time
end=$(date +%s.%N)

# Extract fields
user=$(grep "User time" "$tmp" | awk -F': ' '{print $2}')
sys=$(grep "System time" "$tmp" | awk -F': ' '{print $2}')
maxrss=$(grep "Maximum resident set size" "$tmp" | awk -F': ' '{print $2}')

sqlite3 "$dbpath" <<EOF
UPDATE ${db} SET
  timestampstart        = '$start',
  timestampend          = '$end',
  error                 = '$errorstatus',
  stdout                = '$(sed "s/'/''/g" "$stdout_log")',
  stderr                = '$(sed "s/'/''/g" "$stderr_log")',
  command               = '${cmd[@]}',
  Realtime              = '$real',
  Usertime              = '$user',
  Systime               = '$sys',
  MaxRSS                = '$maxrss_gb',
  slurmdnodename        = '$SLURMD_NODENAME',
  slurmclustername      = '$SLURM_CLUSTER_NAME',
  slurmjobid            = '$SLURM_JOBID',
  slurmjobaccount       = '$SLURM_JOB_ACCOUNT',
  slurmjobname          = '$SLURM_JOB_NAME',
  slurmjobnodelist      = '$SLURM_JOB_NODELIST',
  slurmjobnumnodes      = '$SLURM_JOB_NUM_NODES',
  slurmjobpartition     = '$SLURM_JOB_PARTITION',
  slurmjobqos           = '$SLURM_JOB_QOS',
  slurmjobuid           = '$SLURM_JOB_UID',
  slurmjobuser          = '$SLURM_JOB_USER',
  slurmnprocs           = '$SLURM_NPROCS',
  slurmntasks           = '$SLURM_NTASKS',
  slurmprocid           = '$SLURM_PROCID',
  slurmstepid           = '$SLURM_STEPID',
  slurmstepnodelist     = '$SLURM_STEP_NODELIST',
  slurmstepnumnodes     = '$SLURM_STEP_NUM_NODES',
  slurmstepnumtasks     = '$SLURM_STEP_NUM_TASKS',
  slurmsteptaskspernode = '$SLURM_STEP_TASKS_PER_NODE',
  slurmsubmitdir        = '$SLURM_SUBMIT_DIR',
  slurmsubmithost       = '$SLURM_SUBMIT_HOST',
  slurmtaskspernode     = '$SLURM_TASKS_PER_NODE'
WHERE hash = '$dbhash';
EOF

# Convert KB → GB
maxrss_gb=$(echo "scale=3; $maxrss / (1024*1024)" | bc)

# Compute real time
real=$(echo "$end - $start" | bc)

rm "$tmp"

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
