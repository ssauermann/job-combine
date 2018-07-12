from setuptools import setup, find_packages

setup(
    name='job-combine',
    version='1.1.0',
    packages=find_packages(),
    url='https://github.com/ssauermann/job-combine',
    license='MIT',
    author='Sascha Sauermann',
    author_email='saschasauermann@gmx.de',
    description='Combine similar job scripts for workload managers like SLURM or Loadleveler into fewer scripts '
                'executing the original jobs sequentially to prevent wasting resources when running multiple short '
                'scripts.',
    entry_points={
        'console_scripts': [
            'job-combine = job_combine.job_combine:main',
        ],
    }, test_requires=['pytest'], install_requires=[]
)
