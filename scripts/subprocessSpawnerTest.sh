#!/bin/bash

for i in `seq 0 9`; do
  print $i
  srun -n 1 --mem=0 --exclusive sleep.sh &
done


# we need to wait for all srun tasks to finish
wait
sbatch subprocessSpawnerTest.sh