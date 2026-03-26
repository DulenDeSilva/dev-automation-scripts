import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =========================
# CONFIG
# =========================
FRONTEND_REPO = Path(r"C:\Treasury-Live1\Portfolio_manager 1")
TARGET_BRANCH = "main"

# Source build output from frontend repo
BUILD_SOURCE = FRONTEND_REPO / "build"

# Nginx-served deployment folder
DEPLOY_ROOT = Path(r"C:\Treasury-Live1\frontend")
DEPLOY_BUILD = DEPLOY_ROOT / "build"

DEPENDENCY_FILES = {"package.json", "package-lock.json"}


def run(cmd, cwd: Path, check=True):
    """
    Run a command in the given folder.
    """
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        shell=False
    )
    if check and result.returncode != 0:
        print(f"\nERROR: {' '.join(cmd)}")
        if result.stdout.strip():
            print("\nSTDOUT:")
            print(result.stdout)
        if result.stderr.strip():
            print("\nSTDERR:")
            print(result.stderr)
        sys.exit(result.returncode)
    return result


def git(args, check=True):
    """
    Run a git command inside frontend repo.
    """
    return run(["git", *args], FRONTEND_REPO, check=check)


def npm(args, check=True):
    """
    Run an npm command inside frontend repo.
    """
    return run(["npm", *args], FRONTEND_REPO, check=check)


def print_step(title: str):
    print(f"\n=== {title} ===")


def ensure_paths():
    """
    Ensure required frontend paths exist.
    """
    if not FRONTEND_REPO.exists():
        print(f"Frontend repo path not found: {FRONTEND_REPO}")
        sys.exit(1)
    DEPLOY_ROOT.mkdir(parents=True, exist_ok=True)


def working_tree_clean():
    """
    Server frontend repo must be clean before deployment.
    """
    result = git(["status", "--porcelain"], check=False)
    return result.returncode == 0 and result.stdout.strip() == ""


def changed_files_between(old_ref: str, new_ref: str):
    """
    Get changed files between two git refs.
    """
    if old_ref == new_ref:
        return []
    result = git(["diff", "--name-only", f"{old_ref}..{new_ref}"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def need_npm_install(changed_files):
    """
    Decide whether npm install is needed.
    """
    if not (FRONTEND_REPO / "node_modules").exists():
        return True
    return any(Path(f).name in DEPENDENCY_FILES for f in changed_files)


def backup_existing_build():
    """
    Backup currently deployed frontend build before replacement.
    """
    if not DEPLOY_BUILD.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DEPLOY_ROOT / f"build_backup_{timestamp}"
    shutil.copytree(DEPLOY_BUILD, backup_path)
    return backup_path


def replace_deployed_build():
    """
    Replace live frontend build with the newly built one.
    """
    if not BUILD_SOURCE.exists():
        print(f"Build output not found: {BUILD_SOURCE}")
        sys.exit(1)

    index_html = BUILD_SOURCE / "index.html"
    if not index_html.exists():
        print(f"Build output invalid. Missing: {index_html}")
        sys.exit(1)

    backup_path = backup_existing_build()
    if backup_path:
        print(f"Backup created: {backup_path}")

    if DEPLOY_BUILD.exists():
        shutil.rmtree(DEPLOY_BUILD)

    shutil.copytree(BUILD_SOURCE, DEPLOY_BUILD)


def main():
    ensure_paths()

    print_step("Checking frontend repo")
    if not working_tree_clean():
        print("Frontend repo has local uncommitted changes on server.")
        print("Please clean the repo before deployment.")
        sys.exit(1)

    print_step("Pulling latest frontend code")
    old_head = git(["rev-parse", "HEAD"]).stdout.strip()
    git(["checkout", TARGET_BRANCH])
    git(["pull", "origin", TARGET_BRANCH])
    new_head = git(["rev-parse", "HEAD"]).stdout.strip()

    changed_files = changed_files_between(old_head, new_head)

    print_step("Changed files")
    if changed_files:
        for f in changed_files:
            print(f" - {f}")
    else:
        print("No new frontend commits pulled.")

    if need_npm_install(changed_files):
        print_step("Installing frontend dependencies")
        npm(["install"])
    else:
        print_step("Dependencies")
        print("No frontend dependency changes detected. Skipping npm install.")

    print_step("Building frontend")
    npm(["run", "build"])

    print_step("Replacing deployed build")
    replace_deployed_build()

    print("\nSUCCESS: frontend deployment completed.")


if __name__ == "__main__":
    main()