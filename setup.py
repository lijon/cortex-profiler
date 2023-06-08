from setuptools import setup

setup(
    name='cortex-profiler',
    version='1.0.0',
    description='PC sampling profiler for ARM Cortex-M',
    py_modules=['cortex_profiler'],
    url='https://github.com/lijon/cortex-profiler',
    author='Jonatan Liljedahl',
    author_email='lijon@kymatica.com',
    entry_points={
        'console_scripts': [
            'cortex_profiler = cortex_profiler:cli',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Embedded Systems',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)