from job_combine.cluster.job import Job, sum_times
from job_combine.job_combine import *

job_a = Job('file_a', 'job-a', 'path/to/dir_a', timedelta(minutes=10), 'a.out', 'a.err', [('param1', 'val1')], 'Slurm')
job_b = Job('file_b', 'job-b', 'path/to/dir_b', timedelta(minutes=20), 'b.out', 'b.err', [('param1', 'val1')], 'Slurm')
job_c = Job('file_c', 'job-c', 'path/to/dir_c', timedelta(minutes=30), 'c.out', 'c.err', [('param1', 'val1')], 'Slurm')

jobs = defaultdict(list)

jobs[job_a].append(job_a)
jobs[job_b].append(job_b)
jobs[job_c].append(job_c)

assert len(jobs) == 1
assert len(jobs[job_a]) == 3


def test_partition_no_constraints():
    part = partition(jobs[job_a])
    assert len(part) == 1
    assert len(part[0]) == 3
    assert sum_times(part[0]) == timedelta(minutes=60)


def test_partition_parallel():
    part = partition(jobs[job_a], parallel=3)
    assert len(part) == 3
    assert len(part[0]) == 1
    assert len(part[1]) == 1
    assert len(part[2]) == 1


def test_partition_max_time():
    part = partition(jobs[job_a], max_time=timedelta(minutes=40))
    assert len(part) == 2
    assert sum_times(part[0]) == timedelta(minutes=30)
    assert sum_times(part[1]) == timedelta(minutes=30)
