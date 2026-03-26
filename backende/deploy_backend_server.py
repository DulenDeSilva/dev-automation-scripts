import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path

# =========================
# CONFIG
# =========================
BACKEND_REPO = Path(r"C:\Treasury-Live1\Portfolio_manager_backend 2")
TARGET_BRANCH = "master"
PM2_APP_NAME = "treasury-live1-backend"

# State file for pause/resume deployment
STATE_FILE = Path(r"C:\Treasury-Live1\scripts\backend_deploy_state.json")

# Files/folders considered DB-sensitive
DB_PATTERNS = [
    "migrations/*",
    "migrations/**/*",
    "db/*",
    "db/**/*",
    "models/*",
    "models/**/*",
    "generated/prisma/*",
    "generated/prisma/**/*",
    "*.sql",
    "*migration*.js",
    "*migrate*.js",
]

# Files that should trigger npm install
DEPENDENCY_PATTERNS = [
    "package.json",
    "package-lock.json",
]

# Sensitive files that should stop deployment for manual review
CONFIG_PATTERNS = [
    ".env",
    ".env.*",
]


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
    Run a git command inside backend repo.
    """
    return run(["git", *args], BACKEND_REPO, check=check)


def npm(args, check=True):
    """
    Run an npm command inside backend repo.
    """
    return run(["npm", *args], BACKEND_REPO, check=check)


def pm2(args, check=True):
    """
    Run a PM2 command inside backend repo.
    """
    return run(["pm2", *args], BACKEND_REPO, check=check)


def print_step(title: str):
    print(f"\n=== {title} ===")


def ensure_repo():
    """
    Ensure backend repo path exists.
    """
    if not BACKEND_REPO.exists():
        print(f"Backend repo path not found: {BACKEND_REPO}")
        sys.exit(1)


def working_tree_clean():
    """
    Server repo must be clean before deployment.
    """
    result = git(["status", "--porcelain"], check=False)
    return result.returncode == 0 and result.stdout.strip() == ""


def normalize(path_str: str) -> str:
    return path_str.replace("\\", "/")


def matches_any(path_str: str, patterns):
    """
    Check whether a changed file matches one of the pattern groups.
    """
    p = normalize(path_str)
    base = Path(p).name
    for pattern in patterns:
        pat = normalize(pattern)
        if fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(base, pat):
            return True
    return False


def changed_files_between(old_ref: str, new_ref: str):
    """
    Get changed files between two git refs.
    """
    if old_ref == new_ref:
        return []
    result = git(["diff", "--name-only", f"{old_ref}..{new_ref}"])
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def detect_groups(changed_files):
    """
    Split changed files into important groups:
    - DB changes
    - dependency changes
    - config-sensitive changes
    """
    db_changes = [f for f in changed_files if matches_any(f, DB_PATTERNS)]
    dependency_changes = [f for f in changed_files if matches_any(f, DEPENDENCY_PATTERNS)]
    config_changes = [f for f in changed_files if matches_any(f, CONFIG_PATTERNS)]
    return db_changes, dependency_changes, config_changes


def need_npm_install(changed_files):
    """
    Decide whether npm install is needed.
    """
    if not (BACKEND_REPO / "node_modules").exists():
        return True
    return any(matches_any(f, DEPENDENCY_PATTERNS) for f in changed_files)


def save_state(old_head: str, new_head: str, changed_files):
    """
    Save deployment state when pausing for manual migration.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "old_head": old_head,
        "new_head": new_head,
        "changed_files": changed_files,
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_state():
    """
    Load paused deployment state for resume mode.
    """
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_state():
    """
    Remove paused deployment state after successful completion.
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def pm2_status():
    """
    Get PM2 status of the backend app.
    """
    result = pm2(["jlist"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        apps = json.loads(result.stdout)
        for app in apps:
            if app.get("name") == PM2_APP_NAME:
                return app.get("pm2_env", {}).get("status")
    except Exception:
        return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Deploy backend on server desktop.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume deployment after manual DB migration."
    )
    args = parser.parse_args()

    ensure_repo()

    print_step("Checking backend repo")
    if not working_tree_clean():
        print("Backend repo has local uncommitted changes on server.")
        print("Please clean the repo before deployment.")
        sys.exit(1)

    if args.resume:
        print_step("Resume backend deployment")
        state = load_state()
        if not state:
            print("No paused deployment state found.")
            print("Run normal deployment first.")
            sys.exit(1)

        changed_files = state.get("changed_files", [])
        _, _, config_changes = detect_groups(changed_files)

        if config_changes:
            print("Sensitive config changes detected. Review manually before resuming:")
            for f in config_changes:
                print(f" - {f}")
            sys.exit(1)

        if need_npm_install(changed_files):
            print_step("Installing backend dependencies")
            npm(["install"])
        else:
            print_step("Dependencies")
            print("No backend dependency changes detected. Skipping npm install.")

        print_step("Restarting backend")
        pm2(["restart", PM2_APP_NAME])

        status = pm2_status()
        print(f"PM2 status: {status}")
        if status != "online":
            print("Backend restart failed or app is not online.")
            sys.exit(1)

        clear_state()
        print("\nSUCCESS: backend deployment resumed and completed.")
        return

    print_step("Pulling latest backend code")
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
        print("No new backend commits pulled.")

    db_changes, _, config_changes = detect_groups(changed_files)

    if config_changes:
        print("\nSensitive config changes detected. Review manually before deployment:")
        for f in config_changes:
            print(f" - {f}")
        sys.exit(1)

    if db_changes:
        save_state(old_head, new_head, changed_files)
        print("\nDatabase-related changes detected:")
        for f in db_changes:
            print(f" - {f}")

        print("\nPause deployment here.")
        print("Run your database migrations manually.")
        print("After migrations complete successfully, resume with:")
        print(r"python C:\Treasury-Live1\scripts\deploy_backend_server.py --resume")
        sys.exit(20)

    if need_npm_install(changed_files):
        print_step("Installing backend dependencies")
        npm(["install"])
    else:
        print_step("Dependencies")
        print("No backend dependency changes detected. Skipping npm install.")

    print_step("Restarting backend")
    pm2(["restart", PM2_APP_NAME])

    status = pm2_status()
    print(f"PM2 status: {status}")
    if status != "online":
        print("Backend restart failed or app is not online.")
        sys.exit(1)

    clear_state()
    print("\nSUCCESS: backend deployment completed.")


if __name__ == "__main__":
    main()