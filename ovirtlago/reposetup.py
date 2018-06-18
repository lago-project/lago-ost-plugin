#!/usr/bin/env python2
# Copyright 2016 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

import functools
import re
import itertools
import shutil
import logging
import os
import tempfile

from lago import log_utils
from lago.utils import (
    run_command,
    LockFile,
)

from ovirtlago import constants, server

LOGGER = logging.getLogger(__name__)
LogTask = functools.partial(log_utils.LogTask, logger=LOGGER)
log_task = functools.partial(log_utils.log_task, logger=LOGGER)


class RepositoryError(Exception):
    pass


class RepositoryMergeError(RepositoryError):
    pass


def merge(output_dir, sources, repoman_config=None):
    """
    Run repoman on ``sources``, creating a new RPM repository in
    ``output_dir``

    Args:
        output_dir(str): Path to create new repository
        sources(list of str): repoman sources
        repoman_config(str): repoman configuration file, if not passed it will
            use default repoman configurations, equivalent to:

            |  [main]
            |  on_empty_source=warn
            |  [store.RPMStore]
            |  on_wrong_distro=copy_to_all
            |  with_srcrpms=false
            |  with_sources=false

    Raises:
        :exc:`RepositoryMergeError`: If repoman command failed.
        :exc:`IOError`: If ``repoman_config`` is passed but does not exists.

    Returns:
        None
    """
    cmd = []
    cmd_suffix = [
        '--option=store.RPMStore.rpm_dir=', output_dir, 'add'
    ] + sources
    if repoman_config is None:
        repoman_params = [
            '--option=main.on_empty_source=warn',
            '--option=store.RPMStore.on_wrong_distro=copy_to_all',
            '--option=store.RPMStore.with_srcrpms=false',
            '--option=store.RPMStore.with_sources=false',
        ]
        cmd = ['repoman'] + repoman_params + cmd_suffix
    else:
        if os.path.isfile(repoman_config):
            cmd = ['repoman', '--config={0}'.format(repoman_config)
                   ] + cmd_suffix
        else:
            raise IOError(
                ('error running repoman, {0} not '
                 'found').format(repoman_config)
            )

    with LogTask('Running repoman'):
        res = run_command(cmd)
        if res.code:
            raise RepositoryMergeError(
                (
                    'Failed merging repoman sources: {0} into directory: {1}, '
                    'check lago.log for repoman output '
                ).format(sources, output_dir)
            )


def with_repo_server(func):
    """
    Context manger that starts an http server which serves
    the prefix's internal_repo. The server will listen on the
    management network's IP, and on port `constans.REPO_SERVER_PORT`

    Args:
        The first argument to the wrapped func should be a
            `lago.prefix.Prefix` instance.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        prefix = args[0]
        with server.repo_server_context(
            gw_ip=prefix.virt_env.get_net().gw(),
            port=constants.REPO_SERVER_PORT,
            root_dir=prefix.paths.internal_repo(),
        ):
            return func(*args, **kwargs)

    return wrapper


def _fix_reposync_issues(reposync_out, repo_path):
    """
    Fix for the issue described at::
        https://bugzilla.redhat.com//show_bug.cgi?id=1399235
        https://bugzilla.redhat.com//show_bug.cgi?id=1332441

    """
    if len(repo_path) == 0 or len(reposync_out) == 0:
        LOGGER.warning(
            (
                'unable to run _fix_reposync_issues, no reposync output '
                'or empty repo path.'
            )
        )
        return
    rpm_regex = r'[a-z]{1}[a-zA-Z0-9._\\-]+'
    wrong_version = re.compile(
        r'(?P<package_name>' + rpm_regex + r'): \[Errno 256\]'
    )
    wrong_release = re.compile(r'(?P<package_name>' + rpm_regex + r') FAILED')
    packages = set(
        itertools.chain(
            wrong_version.findall(reposync_out),
            wrong_release.findall(reposync_out)
        )
    )
    count = 0
    LOGGER.debug(
        'detected package errors in reposync output in repo_path:%s: %s',
        repo_path, ','.join(packages)
    )

    for dirpath, _, filenames in os.walk(repo_path):
        rpms = (
            file for file in filenames
            if file.endswith('.rpm') and dirpath.startswith(repo_path)
        )
        for rpm in rpms:
            if any(map(rpm.startswith, packages)):
                bad_package = os.path.join(dirpath, rpm)
                LOGGER.info('removing conflicting RPM: %s', bad_package)
                os.unlink(bad_package)
                count = count + 1

    if count > 0:
        LOGGER.debug(
            (
                'removed %s conflicting packages, see '
                'https://bugzilla.redhat.com//show_bug.cgi?id=1399235 '
                'for more details.'
            ), count
        )


def sync_rpm_repository(repo_path, yum_config, repos):
    lock_path = os.path.join(repo_path, 'repolock')

    if not os.path.exists(repo_path):
        os.makedirs(repo_path)

    # Avoid cache issues due to repo injection to reposync-config.repo
    tmp_dir = tempfile.mkdtemp(prefix='reposync_')
    tmp_cache_dir = os.path.join(tmp_dir, 'cache')
    os.mkdir(tmp_cache_dir)

    LOGGER.debug('Using {} as cache dir for reposync'.format(tmp_cache_dir))

    reposync_base_cmd = [
        'reposync', '--config', yum_config, '--download_path', repo_path,
        '--newest-only', '--delete', '--cachedir', tmp_cache_dir
    ]
    with LogTask('Running reposync'):
        try:
            for repo in repos:
                with LockFile(lock_path, timeout=180):
                    reposync_cmd = reposync_base_cmd + ['--repoid', repo]
                    ret, out, _ = run_command(reposync_cmd)
                    if not ret:
                        LOGGER.debug(
                            'reposync on repo {}: success.'.format(repo)
                        )
                        continue

                    LOGGER.info('repo: {}: failed, re-running.'.format(repo))
                    _fix_reposync_issues(
                        reposync_out=out,
                        repo_path=os.path.join(repo_path, repo)
                    )
                    ret, _, _ = run_command(reposync_cmd)
                    if not ret:
                        continue

                    LOGGER.info(
                        'repo: {}: failed. clearing cache '
                        'and re-running.'.format(repo)
                    )
                    shutil.rmtree(tmp_cache_dir)
                    os.mkdir(tmp_cache_dir)

                    ret, out, err = run_command(reposync_cmd)
                    if ret:
                        LOGGER.error(
                            'reposync command failed for repoid: {repo_id}\n'
                            'stdout:\n{stdout}\n'
                            'stderr:\n{stderr}'.format(
                                repo_id=repo, stdout=out, stderr=err
                            )
                        )

                        raise RuntimeError(
                            (
                                'Failed to run reposync 3 times '
                                'for repoid: {}, aborting.'
                            ).format(repo)
                        )
        finally:
            LOGGER.debug('Removing temp cache dir {}'.format(tmp_dir))
            shutil.rmtree(tmp_dir)
