from setuptools import setup

try:
    import pypandoc
    long_description = pypandoc.convert_file('README.md', 'rst', extra_args=())
except ImportError:
    import codecs
    long_description = codecs.open('README.md', encoding='utf-8').read()

long_description = '\n'.join(long_description.splitlines())

setup(
    name='httpfind',
    description='Search network for HTTP servers using a regular expression filter',
    long_description=long_description,
    version='1.0.0',
    url='https://github.com/Overboard/httpfind',
    author='Overboard',
    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='http find scan filter',
    packages=['httpfind'],

    install_requires=['aiohttp'],

    entry_points={
        'console_scripts': [
            'httpfind = httpfind.httpfind:cli',
        ],
    }
)
