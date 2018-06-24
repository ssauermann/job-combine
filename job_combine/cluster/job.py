"""Job that can be dispatched on a cluster"""
import re
from datetime import timedelta
from os import path

from job_combine.cluster.managers import managers
from job_combine.utils import paths, time_parser


class Job:

    def __init__(self, file, name, directory, time, stdout, stderr, params, manager_name):
        """
        Create a new job object representing a workload manager job file
        :param file: Path to the job file
        :param name: Name of the job
        :param directory: Path to the job file directory
        :param time: Reserved time for this job as timedelta
        :param stdout: File to pipe the standard out stream into
        :param stderr: File to pipe the standard error stream into
        :param params: list of (key, value) tuples for every other job parameter
        :param manager_name: The workload manager this job file is for
        """
        self.file = file
        self.name = name
        self.directory = directory
        self.time = time
        self.stdout = stdout
        self.stderr = stderr
        self.params = tuple(sorted(params, key=lambda x: x[0]))
        self.manager_name = manager_name

    def __hash__(self):
        return hash((self.manager_name, self.params))

    def __eq__(self, other):
        return (self.manager_name, self.params) == (other.manager_name, other.params)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return '(%s, %s, %s, %s, %s, %s, %s)' \
               % (self.name, str(self.time), self.file, self.directory, self.stdout, self.stderr, self.manager_name)

    def manager(self):
        return managers[self.manager_name]

    def to_string(self):
        m = self.manager()

        def d_format(args, val):
            if val is None:
                return ''  # exclude
            else:
                for ai, arg in enumerate(args):
                    if arg is not None:
                        return m.directive + ' ' + (m.arg_format[ai] % (arg, val)) + '\n'

        ret = '#!/bin/bash -x\n'
        ret += d_format(m.name_args, self.name)
        ret += d_format(m.time_args, time_parser.str_from_timedelta(self.time, m.time_formats[0]))
        ret += d_format(m.directory_args, self.directory)
        ret += d_format(m.stdout_args, self.stdout)
        ret += d_format(m.stderr_args, self.stderr)

        for key, arg_index, value in self.params:
            if value is None:
                ret += m.directive + ' ' + (m.flag_format[arg_index] % key) + '\n'
            else:
                ret += m.directive + ' ' + (m.arg_format[arg_index] % (key, value)) + '\n'

        return ret

    @classmethod
    def from_file(cls, job_file, workload_manager=None):
        """
        Parses a job file to a Job object
        :param job_file: Path to the job file
        :param workload_manager: Name of the workload manager this script is for
        :return: Job object
        """
        if workload_manager is not None:
            try:
                manager = managers[workload_manager]
                print('Using workload manager: %s' % manager.name)
            except KeyError:
                raise ValueError('Workload manager not supported: %s' % workload_manager)
        else:
            manager = None

        directory = paths.abs_folder(job_file)
        name = None
        time = timedelta()  # zero
        stdout = None
        stderr = None
        params = []

        with open(job_file, 'r') as f:
            for line in f:
                if line.startswith('#!'):  # shebang
                    pass
                elif line.startswith('# '):  # comment, can not be a job directive
                    pass
                elif line.startswith('#'):  # directive

                    # infer workload manager via directive
                    if manager is None:
                        for wm in managers.values():
                            if line.startswith(wm.directive):
                                manager = wm
                                print('Inferred workload manager: %s' % manager.name)
                                break

                    if not line.startswith(manager.directive):
                        # assume line is a comment as it is no shebang and is not matching the current directive
                        continue

                    # apply all arg and flag regex' to the line
                    matches = [re.search(regex, line) for regex in manager.arg_regex + manager.flag_regex]

                    match = None
                    arg_index = None
                    # get the first successful match
                    for i, m in enumerate(matches):
                        if m is not None:
                            match = m
                            arg_index = i % len(manager.arg_regex)
                            break

                    # no valid match -> can not continue
                    if match is None:
                        raise RuntimeError('Can not process directive `%s`' % line)

                    # get matching results from capture groups; val is None for flags
                    arg = match.group('arg')
                    try:
                        val = match.group('val')
                    except IndexError:
                        val = None

                    if arg == manager.time_args[arg_index]:
                        time = time_parser.str_to_timedelta(val, *manager.time_formats)
                    elif arg == manager.stdout_args[arg_index]:
                        stdout = val
                    elif arg == manager.stderr_args[arg_index]:
                        stderr = val
                    elif arg == manager.directory_args[arg_index]:
                        # working dir could be given relative to job file
                        d = path.expandvars(path.expanduser(arg))  # expand ~/ or env. variables
                        if path.isabs(d):  # TODO Replace path with utils.paths functions
                            directory = d
                        else:
                            directory = path.join(directory, d)
                    elif arg in manager.name_args:
                        name = val
                    else:
                        # Store argument, value pair to be able to decide which scripts can be combined
                        params.append((arg, arg_index, val))

                else:  # script lines
                    pass

        if manager is None:
            raise ValueError('`%s` is not a supported job file' % job_file)

        return cls(paths.abs_path(job_file), name, directory, time, stdout, stderr, params, manager.name)


def sum_times(job_list):
    time = timedelta()
    for job in job_list:
        time += job.time
    return time


def available_managers():
    return managers.keys()
