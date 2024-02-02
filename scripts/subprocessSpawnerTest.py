import subprocess as sps
import os

command = 'srun -n 1 --mem=0 -c 1 --nodes=1 --exclusive ' + os.path.abspath("scripts/sleep.sh")

procs = [ sps.Popen(command, shell=True, stdout=sps.PIPE, stderr=sps.STDOUT) for i in range(0,10) ]
for p in procs:
   p.wait()

for p in procs:
    print(p.communicate()[0].decode("utf-8"))
