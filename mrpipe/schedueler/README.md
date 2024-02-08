# Schedueler Architecture:

This file documents the architecture of the Schedueler / Pipe implementation.
The Pipe is implemented in a modular way, such that individual elements may be replaced. That said, the architecture is implemented with a SLURM cluster in mind.

The general structure comprises four classes:
 - The `Pipe` containing multiple
 - `PipeJob`, each harboring an individual
 - `SLURM.Schedule` with a single defined 
 - `Bash.Script`

The general purpose for each of the class is as follows:

### The Pipe:
The `Pipe` ties everything together and defines the single entry point for the user to submit all processing tasks to.
Processing modules add one or multiple `PipeJobs` to the `Pipe`. 
The `Pipe`iteself will determine how it runs itself and will also distribute processing steps according to its available resources.

### The PipeJob:
The `PipeJob` contains a single pipe step, which usually should be a single processing step or function that is applied parallely to multiple data, i.e. subjects or sessions. 
A `PipeJob` defines dependencies from which the `Pipe` determines the execution order and also provides the necessary interface for the out of memory storage of the whole pipeline.
Out of memory storage is required to provide a self submitting pipeline with multiple independent steps. 
This is provided via pickles. As a final job step, each `PipeJob` submits the following `PipeJob`, which is then unpickled and run.
The alternative would be to have a monitoring job running on the side watching progress and submitting the next steps. 
This wastes resources and the pipe could only run for as long as the monitoring job can maximally run.

### The SLURM.Schedule:
The `SLURM.Schedule` implements the interaction with the SLURM cluster. It defines how to start the job and with which resource allocation to run individual job steps.
It contains a single `Bash.Script` and defines how the module tasks and the required setup steps are implemented in the `Bash.Script`.
It also defines with how many resources each task is to run.  
Specifically it: 
 - communicates the sbatch command to the cluster.
 - translates a list of jobs (i.e. list of strings being a valid bash one-liner) into a srun task submit loop with the appropriate resources.
 - generates the required setup code for the bash file
 - appends the next pipeJob after the srun steps.

### The Bash.Script
The `Bash.Script` provides the interface to write a list of commands as valid bash job to disk. 
This script is then submitted via the `SLURM.Schedule`. 