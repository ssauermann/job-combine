#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
import sys
from collections import defaultdict
from datetime import timedelta
from difflib import SequenceMatcher
from os import path
from json import JSONDecodeError

import jsonpickle

from job_combine.cluster import job as cjob
from job_combine.utils import paths, time_parser

try:
    import argparse
except ImportError:
    print("argparse module not available; either install it "
          "(https://pypi.python.org/pypi/argparse), or "
          "switch to a Python version that includes it.")
    sys.exit(1)


def read_args():
    parser = argparse.ArgumentParser(description='Combines multiple job files into a single job.')
    subparsers = parser.add_subparsers(help='Select the operation to perform')

    parser_queue = subparsers.add_parser('queue',
                                         help='Performs the partitioning and combination of the currently stored jobs')
    parser_add = subparsers.add_parser('add', help='Add a job for combination with the other stored jobs')
    parser_remove = subparsers.add_parser('remove', help='Remove a job from the stored jobs')
    parser_restart = subparsers.add_parser('restart',
                                           help='Removes all completed job from the stored jobs so the failed '
                                                'jobs can be recombined and restarted by `queue`')
    parser_status = subparsers.add_parser('status', help='Displays information about the currently stored jobs and'
                                                         ' which can be combined')
    parser_clear = subparsers.add_parser('clear', help='Removes all currently stored jobs')

    parser_queue.set_defaults(func=queue)
    parser_add.set_defaults(func=add)
    parser_remove.set_defaults(func=remove)
    parser_restart.set_defaults(func=remove_completed)
    parser_status.set_defaults(func=status)
    parser_clear.set_defaults(func=clear)

    # Arguments for all modes
    parser.add_argument('-s', '--storage-file', default='job_combine.storage',
                        help='Path to the file the added scripts are stored [default: %(default)s]')
    parser.add_argument('-v', '--verbose', action='count', help='Increases verbosity level')

    # Arguments for 'add'
    parser_add.add_argument('job_file', help='Job file containing a single task')
    parser_add.add_argument('-w', '--workload-manager', help='Specifies the type of the job file. Will be inferred from'
                                                             ' the directives in the file, if not set. Valid values are'
                                                             ': [%s]' % (', '.join(cjob.available_managers())))

    # Arguments for 'remove'
    parser_remove.add_argument('job_file', help='Job file containing a single task')
    parser_remove.add_argument('-w', '--workload-manager',
                               help='Specifies the type of the job file. Will be inferred from'
                                    ' the directives in the file, if not set. Valid values are'
                                    ': [%s]' % (', '.join(cjob.available_managers())))

    # Arguments for 'restart'
    parser_restart.add_argument('-w', '--workload-manager',
                                help='Specifies the type of the job files. Will be inferred from'
                                     ' the directives in the files, if not set. Valid values are'
                                     ': [%s]' % (', '.join(cjob.available_managers())))
    parser_restart.add_argument('-d', '--directory', default='scripts',
                                help='Directory to store the combined scripts in'
                                     ' [default: %(default)s]')
    parser_restart.add_argument('--adapt-time', default=1, type=float,
                                help='Value to multiply the original time restraints with. [default: %(default)f]')

    # Arguments for 'queue'
    parser_queue.add_argument('--dispatch', action='store_true', help='Dispatch the combined scripts immediately after'
                                                                      ' creating them')
    parser_queue.add_argument('-d', '--directory', default='scripts', help='Directory to store the combined scripts in'
                                                                           ' [default: %(default)s]')
    parser_queue.add_argument('-t', '--max-time', help='No combined job will have a runtime longer than this value')
    parser_queue.add_argument('-m', '--min-time', help='No combined job will have a runtime with less than this value')
    parser_queue.add_argument('-p', '--parallel', default=1, type=int,
                              help='Tries to distribute the jobs equally to `p` scripts. Constraints may increase or '
                                   'reduce the number of created script files. [default: %(default)i]')
    parser_queue.add_argument('--break-max', action='store_true',
                              help='Break the max_time constraint instead of the min_time constraint if not both can be'
                                   ' fulfilled at the same time.')

    # Arguments for 'status'

    # Arguments for 'clear'

    mode = parser.parse_args()

    if mode.verbose is None:
        mode.verbose = 0

    try:
        mode.func(mode)
    except AttributeError:
        print("Illegal mode. Use -h to get a list of possible options.")


def load(file):
    if not path.isabs(file):
        file_abs = path.join(paths.abs_folder(), file)
    else:
        file_abs = file
    with open(file_abs, 'a+') as f:
        try:
            f.seek(0)
            json = f.read()
            return jsonpickle.decode(json)
        except JSONDecodeError:
            return defaultdict(list)


def store(file, dic):
    if not path.isabs(file):
        file_abs = path.join(paths.abs_folder(), file)
    else:
        file_abs = file
    with open(file_abs, 'w+') as f:
        json = jsonpickle.encode(dic)
        f.write(json)


def combine(jobs):
    assert len(jobs) > 0

    # all scripts have params and manager in common or they would not be combinable
    params = jobs[0].params
    manager = jobs[0].manager_name

    # properties of the combined job
    time = cjob.sum_times(jobs)
    stdout = 'job.out'
    stderr = 'job.err'

    # find longest common substring of the names
    best_match = jobs[0].name
    for job in jobs:
        match = SequenceMatcher(None, job.name, best_match) \
            .find_longest_match(0, len(job.name), 0, len(best_match))
        best_match = jobs[0].name[match.a:match.a + match.size]
    name = best_match if best_match.strip() != '' else 'Job'

    c_job = cjob.Job(None, name, None, time, stdout, stderr, params, manager)

    # create script for combined job that calls every original script in its working directory
    c_script = 'cwd=$(pwd)\n'
    for job in jobs:
        c_script += 'cd "%s"\n' % job.directory  # change to working directory
        c_script += '"%s"' % job.file  # execute script (file path is absolute)
        if job.stdout is not None:
            c_script += ' >%s' % stdout  # pipe stdout
        if job.stderr is not None:
            c_script += ' 2>%s' % stderr  # pipe stderr
        c_script += '\n'
        c_script += 'echo %s >> $cwd/done\n\n' % job.file

    return c_job, c_script


def partition(jobs, max_time=timedelta.max, min_time=timedelta(), parallel=1, break_max=True):
    if max_time < min_time:
        raise ValueError('Max time has to be larger than min time')

    print('\nPartitioning results for %i combinable scripts:' % len(jobs))

    # greedy balanced partitioning into n groups considering the time constraints
    def do_partition(target_n, previous=-1):
        part = []

        desc_jobs = sorted(jobs, key=lambda x: x.time, reverse=True)

        # create each partition and fill them with the n largest items
        for _ in range(target_n):
            part.append([desc_jobs.pop(0)])

        # iterate over the remaining items and fill the largest item into the smallest partition
        for j in desc_jobs:
            smallest_part = min(part, key=cjob.sum_times)
            smallest_part.append(j)

        # validate time constraints
        for p in part:
            time = cjob.sum_times(p)
            if time > max_time:
                if target_n >= len(jobs):
                    print('WARNING: Could not fulfill max_time = %s constraint as there exists a single script with a'
                          ' longer time.' % max_time)
                    break
                if previous == target_n + 1 and break_max:  # fluctuating around target_n and target_n + 1
                    print('WARNING: Could not fulfill both time constraints simultaneously.'
                          ' Breaking the max_time = %s constraint.' % max_time)
                    break
                return do_partition(target_n + 1, target_n)  # need more partitions
            elif time < min_time:
                if target_n == 1:
                    print(
                        'WARNING: Could not fulfill min_time = %s constraint as there are not enough combinable scripts'
                        ' to reach this time.' % min_time)
                    break
                if previous == target_n - 1 and not break_max:  # fluctuating around target_n and target_n + 1
                    print('WARNING: Could not fulfill both time constraints simultaneously.'
                          ' Breaking the min_time = %s constraint.' % min_time)
                    break
                return do_partition(target_n - 1, target_n)  # need fewer partitions

        # constraint check successful
        return part

    target_number = min(parallel, len(jobs))
    part_result = do_partition(target_number)
    if len(part_result) > parallel > 1:
        print('WARNING: Could not partition the jobs to less than %i partitions. Try relaxing the max_time'
              ' constraint.' % parallel)
    times = [str(cjob.sum_times(p)) for p in part_result]
    print('%i partitions with times: %s' % (len(part_result), ', '.join(times)))

    return part_result


def queue(args):
    current_jobs = load(args.storage_file)

    dir_counter = 0

    time_format = '%H:%M:%S'
    if args.max_time is None:
        max_time = timedelta.max
    else:
        max_time = time_parser.str_to_timedelta(args.max_time, time_format)
    if args.min_time is None:
        min_time = timedelta()
    else:
        min_time = time_parser.str_to_timedelta(args.min_time, time_format)

    print('Combining scripts...')

    for similar_jobs in current_jobs.values():
        if len(similar_jobs) == 0:
            continue

        # partition jobs based on constraints
        part = partition(similar_jobs, max_time, min_time, args.parallel, args.break_max)
        # combine scripts in same partition
        combined = map(combine, part)

        # create separate sub folder for each script and write them to files
        for job, script in combined:
            script_dir = paths.abs_path(path.join(args.directory, '%02i' % dir_counter))
            dir_counter += 1
            os.makedirs(script_dir, exist_ok=True)

            job.file = path.join(script_dir, 'submit.job')
            job.directory = script_dir

            # write directives and combined script to file
            with open(job.file, 'w+') as f:
                f.write(job.to_string())
                f.write('\n')
                f.write(script)

            if int(args.verbose) >= 1:
                print('Written script to %s' % job.file)
            if args.dispatch:
                if os.system(job.manager().dispatch_command + ' ' + job.file) == 0:
                    if int(args.verbose) >= 1:
                        print('Dispatching successful for: %s' % job.file)
    print('Done combining scripts.')


def add(args):
    current_jobs = load(args.storage_file)

    job = cjob.Job.from_file(args.job_file, args.workload_manager)
    os.chmod(job.file, os.stat(job.file).st_mode | 0o111)  # set script executable for everyone
    current_jobs[job.key()].append(job)

    store(args.storage_file, current_jobs)
    print('Added job successfully.')


def remove(args):
    current_jobs = load(args.storage_file)

    job = cjob.Job.from_file(args.job_file, args.workload_manager)
    current_jobs[job.key()].remove(job)

    store(args.storage_file, current_jobs)
    print('Removed job successfully.')


def remove_completed(args):
    current_jobs = load(args.storage_file)
    script_dir = args.directory

    completed_scripts = []
    for root, dirs, files in os.walk(script_dir):
        for f in files:
            if f == 'done':
                with open(path.join(root, f)) as file:
                    completed_scripts += [line.strip() for line in file]

    for script_f in completed_scripts:
        job = cjob.Job.from_file(script_f, args.workload_manager)
        current_jobs[job.key()].remove(job)

    if args.adapt_time != 1:
        for similar_jobs in current_jobs.values():
            for job in similar_jobs:
                job.time *= args.adapt_time

    store(args.storage_file, current_jobs)
    print('Removed %i jobs successfully.' % len(completed_scripts))


def status(args):
    jobs = load(args.storage_file)
    n_jobs = sum([len(v) for v in jobs.values()])

    times = []
    for k, v in jobs.items():
        if len(v) == 0:
            continue
        time_format = v[0].manager().time_formats[0]
        time_sum = cjob.sum_times(v)
        times.append(time_parser.str_from_timedelta(time_sum, time_format))

    min_combined_jobs = len(jobs)

    print('Stored %i jobs that can be combined to %i tasks with the times [%s].'
          % (n_jobs, min_combined_jobs, ', '.join(times)))

    if int(args.verbose) >= 1:
        print('\n', jobs.items())


def clear(args):
    os.remove(args.storage_file)
    print('Deleted storage file.')


def main():
    read_args()


if __name__ == "__main__":
    main()
