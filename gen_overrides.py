# gen-overrides.py
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyproject-parser",
#   "requirements-parser",
# ]
# ///
# SPDX-License-Identifier: BSD-2-Clause
import os
import subprocess
import sys
import urllib
from pathlib import Path

from pyproject_parser import PyProject

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

rootdir = Path(os.environ["PDM_PROJECT_ROOT"])

def get_branch(repo_dir):
    """Get the current git branch"""
    return subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()

def get_remote_branch_commit(repo, branch):
    """Get the commit hash for a remote branch, or None if it doesn't exist"""
    try:
        output = subprocess.check_output(
            ['git', 'ls-remote', repo, f'refs/heads/{branch}'],
            text=True, stderr=subprocess.DEVNULL)
        if output:
            # Output format: "<commit_hash>\trefs/heads/<branch>"
            return output.split()[0]
    except subprocess.CalledProcessError:
        pass
    return None

def gen_overrides():
    if len(sys.argv) > 2:
        branch = sys.argv[1]
        if branch.startswith("refs/heads/"):
            branch = branch[11:]
        base_branch = sys.argv[2]
        if base_branch.startswith("refs/heads/"):
            base_branch = base_branch[11:]

    else:
        branch = get_branch(rootdir)
        base_branch = get_branch(rootdir)
    prj = PyProject.load(rootdir / "pyproject.toml")
    reqs = prj.project['dependencies']
    git_reqs = [r for r in reqs if r.url and r.url.startswith('git+')]
    for r in git_reqs:
        parts = urllib.parse.urlparse(r.url, allow_fragments=True)
        # remove any branches that might already be there
        base = parts.path.rsplit(sep="@",maxsplit=1)[0]
        clone_url = urllib.parse.urlunparse(parts._replace(path=base, scheme="https"))
        eprint(f"# Checking {branch} and {base_branch} on {clone_url}")
        commit = get_remote_branch_commit(clone_url, branch)
        if commit:
            eprint(f"#    {branch} found! Using commit {commit[:8]}")
            path = f"{base}@{commit}"
        else:
            commit = get_remote_branch_commit(clone_url, base_branch)
            if commit:
                eprint(f"#    {base_branch} found! Using commit {commit[:8]}")
                path = f"{base}@{commit}"
            else:
                eprint("#    not found, falling back to main")
                path = parts.path
        r.url = urllib.parse.urlunparse(parts._replace(path=path))
        print(str(r))

if __name__ == "__main__":
    gen_overrides()
