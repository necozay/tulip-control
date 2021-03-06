#!/usr/bin/env python
import logging
from setuptools import setup
import subprocess
import os


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Topic :: Scientific/Engineering']
package_data = {
    'tulip': ['commit_hash.txt'],
    'tulip.transys.export': ['d3.v3.min.js'],
    'tulip.spec': ['parsetab.py']}


def retrieve_git_info():
    """Return commit hash of HEAD, or "release", or None if failure.

    If the git command fails, then return None.

    If HEAD has tag with prefix "tulip-" or "vM" where M is an
    integer, then return 'release'.
    Tags with such names are regarded as version or release tags.

    Otherwise, return the commit hash as str.
    """
    # Is Git installed?
    try:
        subprocess.call(['git', '--version'],
                        stdout=subprocess.PIPE)
    except OSError:
        return None
    # Decide whether this is a release
    p = subprocess.Popen(
        ['git', 'describe', '--tags', '--candidates=0', 'HEAD'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    p.wait()
    if p.returncode == 0:
        tag = p.stdout.read()
        logger.debug('Most recent tag: ' + tag)
        if tag.startswith('tulip-'):
            return 'release'
        if len(tag) >= 2 and tag.startswith('v'):
            try:
                int(tag[1])
                return 'release'
            except ValueError:
                pass
    # Otherwise, return commit hash
    p = subprocess.Popen(
        ['git', 'log', '-1', '--format=%H'],
        stdout=subprocess.PIPE)
    p.wait()
    sha1 = p.stdout.read()
    logger.debug('SHA1: ' + sha1)
    return sha1


def package_jtlv():
    if os.path.exists(os.path.join('tulip', 'interfaces', 'jtlv_grgame.jar')):
        print('Found optional JTLV-based solver.')
        package_data['tulip.interfaces'] = ['jtlv_grgame.jar']
    else:
        print('The jtlv synthesis tool was not found. '
              'Try extern/get-jtlv.sh to get it.\n'
              'It is an optional alternative to gr1c, '
              'the default GR(1) solver of TuLiP.')


def run_setup():
    # Build PLY table, to be installed as tulip package data
    try:
        import tulip.spec.lexyacc
        tabmodule = tulip.spec.lexyacc.TABMODULE.split('.')[-1]
        outputdir = 'tulip/spec'
        parser = tulip.spec.lexyacc.Parser()
        parser.build(tabmodule, outputdir=outputdir,
                     write_tables=True,
                     debug=True, debuglog=logger)
        plytable_build_failed = False
    except Exception as e:
        logger.debug('Failed to build PLY tables: {e}'.format(e=e))
        plytable_build_failed = True
    # If .git directory is present, create commit_hash.txt accordingly
    # to indicate version information
    if os.path.exists('.git'):
        # Provide commit hash or empty file to indicate release
        sha1 = retrieve_git_info()
        if sha1 is None:
            sha1 = 'unknown-commit'
        elif sha1 is 'release':
            sha1 = ''
        else:
            logger.debug('dev sha1: ' + str(sha1))
        commit_hash_header = (
            '# DO NOT EDIT!  '
            'This file was automatically generated by setup.py of TuLiP')
        with open("tulip/commit_hash.txt", "w") as f:
            f.write(commit_hash_header + "\n")
            f.write(sha1 + "\n")
    # Import tulip/version.py without importing tulip
    import imp
    version = imp.load_module("version",
                              *imp.find_module("version", ["tulip"]))
    tulip_version = version.version
    # setup
    package_jtlv()
    setup(
        name='tulip',
        version=tulip_version,
        description='Temporal Logic Planning (TuLiP) Toolbox',
        author='Caltech Control and Dynamical Systems',
        author_email='tulip@tulip-control.org',
        url='http://tulip-control.org',
        bugtrack_url='http://github.com/tulip-control/tulip-control/issues',
        license='BSD',
        classifiers=classifiers,
        install_requires=[
            'ply >= 3.4',
            'networkx >= 1.6',
            'numpy >= 1.7',
            'pydot >= 1.0.28',
            'scipy'],
        extras_require={
            'hybrid': ['cvxopt >= 1.1.7',
                       'polytope >= 0.1.1']},
        tests_require=[
            'nose',
            'matplotlib'],
        packages=[
            'tulip', 'tulip.transys', 'tulip.transys.export',
            'tulip.abstract', 'tulip.spec',
            'tulip.interfaces'],
        package_dir={'tulip': 'tulip'},
        package_data=package_data)
    # ply failed ?
    if plytable_build_failed:
        print("!"*65)
        print("    Failed to build PLY table.  Please run setup.py again.")
        print("!"*65)


if __name__ == '__main__':
    run_setup()
