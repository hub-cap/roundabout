""" The Roundabout git module. """

import git
import os
import shutil

from git import Repo, GitCommandError #pylint: disable=E1101
from random import choice
from string import letters #pylint: disable=W0402

from roundabout import log


BUILD_FAIL_MSG = "Build failed, rejecting.\n\n%s"
MERGE_FAIL_MSG = "Merge failed, rejecting.\n\n%s"
BUILD_SUCCESS_MSG = "Build successful! Merged!"


class GitException(BaseException):
    """ Roundabout git exceptions """
    def __init__(self, exc):
        super(GitException, self).__init__(exc)
        log.error(str(exc))


class Git(object):
    """ Roundabout git package proxy """ 

    def __init__(self, remote_name, remote_url, remote_branch, config):
        self.remote_name = remote_name
        self.remote_url = remote_url
        self.local_branch_name = "merge_%s" % remote_branch
        self.remote_branch = "remotes/%s/%s" % (remote_name, remote_branch)
        self.config = config

        cn = "".join([choice(letters) for i in range(8)]) #pylint: disable=W0612
        self.clonepath = os.path.join(config["git"]["local_repo_path"], cn)
        try:
            self.repo = Repo.clone_from(config["git"]["base_repo_url"],
                                        self.clonepath)
        except GitCommandError, e:
            raise GitException(e)

    def __enter__(self):
        self.remote.fetch()
        return self

    def __exit__(self, *args):
        self.cleanup()

    @property
    def remote(self):
        """ Create and return the remote object """
        self.repo.create_remote(self.remote_name, self.remote_url)
        return [remote for remote
                       in self.repo.remotes
                       if remote.name == self.remote_name][0]

    def branch(self, branch):
        """ Return the head object referenced by the branch name """
        return [b for b in self.repo.branches if branch == b.name][0]

    def cleanup(self):
        """
        Delete the remote merge branch and the temporary cloned repo. If the
        local_branch_name is master (which can't happen in the normal workflow)
        or shutil.rmtree raises an OSError we raise GitException.
        """
        if self.local_branch_name == 'master':
            raise GitException("Attempted to delete your remote master!")
        
        self.push(":%s" % self.local_branch_name)
        try:
            shutil.rmtree(self.clonepath)
        except OSError, e:
            raise GitException(e)

    def merge(self, branch, squash=None, message=None):
        """ Merge the passed in branch with HEAD """

        log.info("merging %s into %s" % (branch, self.repo.active_branch.name))
        merge_cmd = ('git', 'merge', branch)
        try:
            if squash:
                squash_cmd = tuple(list(merge_cmd) + ['--squash'])
                self.repo.git.execute(squash_cmd)

                if not message:
                    try:
                        with open(self.clonepath + "/.git/SQUASH_MSG") as msg:
                            message = msg.read()
                    except IOError:
                        message = "Squash merge %s into %s" % (branch,
                            self.repo.active_branch.name)

                commit_cmd = ['git', 'commit', '-m']
                commit_cmd.append(message)
                return self.repo.git.execute(tuple(commit_cmd))
            else:
                return self.repo.git.execute(merge_cmd)
        except git.exc.GitCommandError, e:
            # If there's a merge failure reset and raise.
            self.repo.head.reset(working_tree=True)
            raise GitException(e)

    def push(self, branch, remote='origin', remote_branch=None):
        """ Push the branch up to the remote """
        if remote_branch:
            branch = "%s:%s" % (branch, remote_branch)
        log.info("pushing %s to %s" % (branch, remote))
        return self.repo.remote(remote).push(branch)
