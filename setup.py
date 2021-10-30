from setuptools import setup, find_packages

setup(
    name='wt_tools',
    author='klensy',
    description='War Thunder resource extraction tools',
    url='https://github.com/klensy/wt-tools',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={'wt_tools': ['formats/blk.lark']},
)
