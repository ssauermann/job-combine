# job-combine [![Build Status](https://travis-ci.org/ssauermann/job-combine.svg?branch=master)](https://travis-ci.org/ssauermann/job-combine) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/8b82edb96d234438a40129e33d67df41)](https://www.codacy.com/app/ssauermann/job-combine?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ssauermann/job-combine&amp;utm_campaign=Badge_Grade)
Combine similar job scripts for workload managers like SLURM or Loadleveler into fewer scripts executing the original
 jobs sequentially to prevent wasting resources when running multiple short scripts.

## Requirements
- Python &ge; 3.3 or Python &ge; 2.6 with argparse

## Installation
- Install directly from github with `pip install git+https://github.com/ssauermann/job-combine`

**Note**: 
You probably need the `--user` flag to install the package only for your user.
Make sure `~/.local/bin` is on your `PATH` and `~/.local/lib/pythonX.Y/site-packages` is on your `PYTHONPATH`.

## Usage
See the full help by executing `job-combine -h` or `job-combine <mode> -h`
- Adding job files:
`job-combine add <path to job file>`
- Removing job files:
`job-combine remove <path to job file>`
- Remove all currently stored job files:
`job-combine clear`
- Print short overview over stored job files:
`job-combine status`
- Perform the partitioning and combine the job files:
`job-combine queue`
    - `-t <time limit for a single combined job>`
    - `-m <minimum run time for a single combined job>`
    - `-p <number of combined jobs to target>`
    - `--dispatch` Queue combined jobs directly after creation
- Remove all jobs that ran successfully from the storage:
`job-combine restart`
    - `--adapt-time <multiplier>` Multiple the times of the scripts that have not yet been completed by this amount
## Example usage
1. Create job scripts programmatically and call `job-combine -s ~/job.storage add <jobfile>` for each one.
2. Combine the scripts considering the following constraints:
    - Run time limit of a job is 48 hours
    - Scripts should run at least 10 minutes
    - Up to 50 jobs can be queued simultaneously
    - `job-combine -s ~/job.storage queue -d ~/combined -t 48:0:0 -m 0:10:0 -p 50`
3. Check the output of 2. and verify that all constraints could be fulfilled or some had to be broken.
4. Queue the job files that can be found in `~/combined/[00-49]/` manually or execute the same command as in 2. with
 `--dispatch` as additional parameter.
5. The output files of the original jobs can be found where they would be if they were executed directly.
6. Clear storage for the next execution: `job-combine -s ~/job.storage clear`

## What scripts can be combined?
Scripts may differ in:
- Job name
- Wall time limit
- Std out and std err files
- Type of shell the job script is executed in (i.e. the shebang may differ)
- The script itself

Jobs that differ in other parameters like number of nodes can not be combined.
The partitioning and combination will be applied to each group of combinable jobs separately.
So adding two jobs with 1 node and three scripts with 2 nodes will result in two combined jobs: one script for 1 node and another one for 2 nodes.