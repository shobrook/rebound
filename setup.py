from setuptools import setup

setup(
    name="rebound",
    version='0.1',
    py_modules=['rebound'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        rebound=rebound:rebound
    ''',
)
