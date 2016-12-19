from setuptools import setup, find_packages

def read_file(name):
    with open(name, 'r', encoding='utf-8') as f:
        return f.read()


setup(
    name='barpyrus',
    version='0.0.0',
    description='A python wrapper for lemonbar/conky',
    long_description=read_file('README.md'),
    url='https://github.com/t-wissmann/barpyrus',
    author='Thorsten Wißmann',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: X11 Applications',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Topic :: Desktop Environment',
    ],
    packages=find_packages(include=['barpyrus']),
    entry_points={
        'console_scripts': [
            'barpyrus=barpyrus.mainloop:main',
        ],
    },
)
