#!/usr/bin/env python3
"""
=============================================================================
CodeForge AI - HuggingFace Spaces Deployment Script
=============================================================================
Automated deployment to HuggingFace Spaces using the huggingface_hub library.

Usage:
    python deploy_to_huggingface.py [OPTIONS]

Options:
    --space-name NAME      Name for the HF Space (default: codeforge-ai)
    --username USERNAME    HuggingFace username (or uses HF_USERNAME env var)
    --token TOKEN          HuggingFace token (or uses HF_TOKEN env var)
    --private              Make the Space private
    --gradio-only          Deploy lightweight Gradio version only
    --update               Update existing Space instead of creating new
    --sync-secrets         Sync local .env secrets to HF Space
    --hardware TIER        Hardware tier: cpu-basic, cpu-upgrade, t4-small, etc.

Examples:
    # Create new public Space
    python deploy_to_huggingface.py --space-name my-codeforge

    # Update existing Space
    python deploy_to_huggingface.py --space-name my-codeforge --update

    # Deploy Gradio-only version
    python deploy_to_huggingface.py --gradio-only
=============================================================================
"""

import os
import sys
import argparse
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

try:
    from huggingface_hub import (
        HfApi,
        create_repo,
        upload_folder,
        upload_file,
        CommitOperationAdd,
        login,
        whoami,
        space_info,
    )
    from huggingface_hub.utils import RepositoryNotFoundError
except ImportError:
    print("Error: huggingface_hub not installed. Run: pip install huggingface_hub")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_SPACE_NAME = "codeforge-ai"
DEFAULT_HARDWARE = "cpu-basic"

# Files to include in deployment
CORE_FILES = [
    "backend/",
    "hf_requirements.txt",
    "start.sh",
    "supervisord.conf",
]

FULL_DEPLOYMENT_FILES = CORE_FILES + [
    "frontend/",
    "Dockerfile",
]

GRADIO_DEPLOYMENT_FILES = [
    "backend/",
    "gradio_app.py",
    "Dockerfile.gradio",
    "hf_requirements_gradio.txt",
]

# Files to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".env",
    ".env.local",
    "node_modules",
    ".next",
    "venv",
    "*.log",
    "*.db",
    "*.sqlite",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
]

# Secrets to sync (keys from local .env)
SECRET_KEYS = [
    "VENICE_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "SECRET_KEY",
]

# Variables to sync (non-sensitive)
VARIABLE_KEYS = [
    "GITHUB_USERNAME",
    "DEFAULT_AI_PROVIDER",
    "LOG_LEVEL",
]


# =============================================================================
# Helper Functions
# =============================================================================

def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step: int, total: int, text: str):
    """Print a step indicator."""
    print(f"\n[{step}/{total}] {text}")


def print_success(text: str):
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str):
    """Print error message."""
    print(f"❌ {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"⚠️  {text}")


def print_info(text: str):
    """Print info message."""
    print(f"ℹ️  {text}")


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    return env_vars


def create_temp_deployment_dir(
    source_dir: Path,
    files_to_include: List[str],
    gradio_only: bool = False
) -> Path:
    """Create a temporary directory with deployment files."""
    import tempfile
    
    temp_dir = Path(tempfile.mkdtemp(prefix="codeforge_deploy_"))
    
    for item in files_to_include:
        src = source_dir / item
        if not src.exists():
            print_warning(f"File not found, skipping: {item}")
            continue
            
        dst = temp_dir / item
        
        if src.is_dir():
            shutil.copytree(
                src, dst,
                ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS)
            )
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    # Copy and rename specific files for HF Spaces
    if gradio_only:
        # For Gradio: rename Dockerfile.gradio to Dockerfile
        gradio_dockerfile = temp_dir / "Dockerfile.gradio"
        if gradio_dockerfile.exists():
            shutil.move(gradio_dockerfile, temp_dir / "Dockerfile")
        
        # Copy gradio_app.py as app.py
        gradio_app = source_dir / "gradio_app.py"
        if gradio_app.exists():
            shutil.copy2(gradio_app, temp_dir / "app.py")
        
        # Rename requirements
        gradio_req = temp_dir / "hf_requirements_gradio.txt"
        if gradio_req.exists():
            shutil.move(gradio_req, temp_dir / "requirements.txt")
    else:
        # For full deployment: use main Dockerfile
        main_req = temp_dir / "hf_requirements.txt"
        if main_req.exists():
            shutil.copy2(main_req, temp_dir / "requirements.txt")
    
    # Copy HF README
    hf_readme = source_dir / "HF_README.md"
    if hf_readme.exists():
        shutil.copy2(hf_readme, temp_dir / "README.md")
    
    return temp_dir


# =============================================================================
# Deployment Functions
# =============================================================================

def authenticate(token: Optional[str] = None) -> HfApi:
    """Authenticate with HuggingFace Hub."""
    api = HfApi()
    
    # Try to use token from argument, env var, or prompt
    hf_token = token or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    
    if not hf_token:
        print_info("No HF_TOKEN found. Please login interactively or set HF_TOKEN env var.")
        try:
            login()
        except Exception as e:
            print_error(f"Authentication failed: {e}")
            sys.exit(1)
    else:
        try:
            login(token=hf_token)
        except Exception as e:
            print_error(f"Token authentication failed: {e}")
            sys.exit(1)
    
    # Verify authentication
    try:
        user = whoami()
        print_success(f"Authenticated as: {user['name']}")
        return api
    except Exception as e:
        print_error(f"Failed to verify authentication: {e}")
        sys.exit(1)


def check_space_exists(api: HfApi, repo_id: str) -> bool:
    """Check if a Space already exists."""
    try:
        space_info(repo_id)
        return True
    except RepositoryNotFoundError:
        return False


def create_space(
    api: HfApi,
    repo_id: str,
    private: bool = False,
    hardware: str = DEFAULT_HARDWARE
) -> str:
    """Create a new HuggingFace Space."""
    try:
        repo_url = create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=private,
            exist_ok=False
        )
        print_success(f"Created Space: {repo_url}")
        return str(repo_url)
    except Exception as e:
        if "already exists" in str(e).lower():
            print_warning(f"Space {repo_id} already exists. Use --update to update it.")
            return f"https://huggingface.co/spaces/{repo_id}"
        raise e


def upload_deployment(
    api: HfApi,
    repo_id: str,
    source_dir: Path,
    gradio_only: bool = False
) -> str:
    """Upload deployment files to the Space."""
    
    # Determine which files to include
    if gradio_only:
        files_to_include = GRADIO_DEPLOYMENT_FILES
    else:
        files_to_include = FULL_DEPLOYMENT_FILES
    
    print_info(f"Preparing deployment files...")
    temp_dir = create_temp_deployment_dir(source_dir, files_to_include, gradio_only)
    
    try:
        print_info(f"Uploading to {repo_id}...")
        
        # Upload the entire folder
        upload_folder(
            folder_path=str(temp_dir),
            repo_id=repo_id,
            repo_type="space",
            commit_message=f"Deploy CodeForge AI - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        print_success("Files uploaded successfully!")
        return f"https://huggingface.co/spaces/{repo_id}"
        
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def sync_secrets(api: HfApi, repo_id: str, env_path: Path):
    """Sync secrets from local .env to HF Space."""
    
    if not env_path.exists():
        print_warning(f"No .env file found at {env_path}")
        return
    
    env_vars = load_env_file(env_path)
    
    print_info("Syncing secrets to HuggingFace Space...")
    
    for key in SECRET_KEYS:
        if key in env_vars and env_vars[key]:
            try:
                api.add_space_secret(
                    repo_id=repo_id,
                    key=key,
                    value=env_vars[key]
                )
                print_success(f"Secret '{key}' synced")
            except Exception as e:
                print_warning(f"Failed to sync secret '{key}': {e}")
    
    for key in VARIABLE_KEYS:
        if key in env_vars and env_vars[key]:
            try:
                api.add_space_variable(
                    repo_id=repo_id,
                    key=key,
                    value=env_vars[key]
                )
                print_success(f"Variable '{key}' synced")
            except Exception as e:
                print_warning(f"Failed to sync variable '{key}': {e}")


def monitor_build(api: HfApi, repo_id: str, timeout: int = 600):
    """Monitor Space build status."""
    
    print_info("Monitoring build status...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            info = space_info(repo_id)
            runtime = info.runtime
            
            if runtime:
                stage = runtime.get("stage", "unknown")
                
                if stage == "RUNNING":
                    print_success("Space is now running!")
                    return True
                elif stage in ["BUILDING", "STARTING"]:
                    print(f"  Status: {stage}...", end="\r")
                elif stage == "BUILD_ERROR":
                    print_error("Build failed! Check Space logs for details.")
                    return False
                elif stage == "RUNTIME_ERROR":
                    print_error("Runtime error! Check Space logs for details.")
                    return False
            
            time.sleep(10)
            
        except Exception as e:
            print_warning(f"Error checking status: {e}")
            time.sleep(10)
    
    print_warning("Build monitoring timed out. Check Space status manually.")
    return None


# =============================================================================
# Main Deployment Function
# =============================================================================

def deploy(
    space_name: str = DEFAULT_SPACE_NAME,
    username: Optional[str] = None,
    token: Optional[str] = None,
    private: bool = False,
    gradio_only: bool = False,
    update: bool = False,
    sync_secrets_flag: bool = False,
    hardware: str = DEFAULT_HARDWARE,
    monitor: bool = True
):
    """Main deployment function."""
    
    print_header("CodeForge AI - HuggingFace Spaces Deployment")
    
    # Get source directory
    source_dir = Path(__file__).parent.resolve()
    print_info(f"Source directory: {source_dir}")
    
    total_steps = 5 if sync_secrets_flag else 4
    
    # Step 1: Authenticate
    print_step(1, total_steps, "Authenticating with HuggingFace Hub...")
    api = authenticate(token)
    
    # Get username
    user_info = whoami()
    hf_username = username or os.getenv("HF_USERNAME") or user_info['name']
    repo_id = f"{hf_username}/{space_name}"
    
    print_info(f"Target Space: {repo_id}")
    print_info(f"Deployment type: {'Gradio-only' if gradio_only else 'Full (Next.js + FastAPI)'}")
    print_info(f"Hardware: {hardware}")
    print_info(f"Visibility: {'Private' if private else 'Public'}")
    
    # Step 2: Create or verify Space
    print_step(2, total_steps, "Setting up HuggingFace Space...")
    
    space_exists = check_space_exists(api, repo_id)
    
    if space_exists:
        if not update:
            print_warning(f"Space {repo_id} already exists.")
            response = input("Do you want to update it? (y/n): ").strip().lower()
            if response != 'y':
                print_info("Deployment cancelled.")
                return
        print_info(f"Updating existing Space: {repo_id}")
    else:
        print_info(f"Creating new Space: {repo_id}")
        create_space(api, repo_id, private=private, hardware=hardware)
    
    # Step 3: Upload files
    print_step(3, total_steps, "Uploading deployment files...")
    space_url = upload_deployment(api, repo_id, source_dir, gradio_only)
    
    # Step 4: Sync secrets (optional)
    if sync_secrets_flag:
        print_step(4, total_steps, "Syncing environment secrets...")
        env_path = source_dir / "backend" / ".env"
        sync_secrets(api, repo_id, env_path)
    
    # Step 5: Monitor build
    step = 5 if sync_secrets_flag else 4
    print_step(step, total_steps, "Finalizing deployment...")
    
    if monitor:
        print_info("Waiting for Space to build (this may take a few minutes)...")
        monitor_build(api, repo_id)
    
    # Print summary
    print_header("Deployment Complete!")
    print(f"""
📦 Space URL: {space_url}
🔧 Settings: {space_url}/settings
📊 Logs: {space_url}/logs

Next steps:
1. Visit the Space URL to verify deployment
2. Configure secrets in Space Settings if not synced
3. Check logs if there are any issues

Environment Variables to set in Space Settings:
- VENICE_API_KEY (Secret) - For AI code generation
- GITHUB_PERSONAL_ACCESS_TOKEN (Secret) - For GitHub integration
- GITHUB_USERNAME (Variable) - Your GitHub username
- SECRET_KEY (Secret) - Application secret key
""")


# =============================================================================
# CLI
# =============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy CodeForge AI to HuggingFace Spaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy_to_huggingface.py --space-name my-codeforge
  python deploy_to_huggingface.py --gradio-only --private
  python deploy_to_huggingface.py --update --sync-secrets
        """
    )
    
    parser.add_argument(
        "--space-name",
        default=DEFAULT_SPACE_NAME,
        help=f"Name for the HF Space (default: {DEFAULT_SPACE_NAME})"
    )
    parser.add_argument(
        "--username",
        help="HuggingFace username (or set HF_USERNAME env var)"
    )
    parser.add_argument(
        "--token",
        help="HuggingFace token (or set HF_TOKEN env var)"
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the Space private"
    )
    parser.add_argument(
        "--gradio-only",
        action="store_true",
        help="Deploy lightweight Gradio version only"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing Space instead of creating new"
    )
    parser.add_argument(
        "--sync-secrets",
        action="store_true",
        help="Sync local .env secrets to HF Space"
    )
    parser.add_argument(
        "--hardware",
        default=DEFAULT_HARDWARE,
        choices=["cpu-basic", "cpu-upgrade", "t4-small", "t4-medium", "a10g-small", "a10g-large"],
        help=f"Hardware tier (default: {DEFAULT_HARDWARE})"
    )
    parser.add_argument(
        "--no-monitor",
        action="store_true",
        help="Don't monitor build status after deployment"
    )
    
    args = parser.parse_args()
    
    try:
        deploy(
            space_name=args.space_name,
            username=args.username,
            token=args.token,
            private=args.private,
            gradio_only=args.gradio_only,
            update=args.update,
            sync_secrets_flag=args.sync_secrets,
            hardware=args.hardware,
            monitor=not args.no_monitor
        )
    except KeyboardInterrupt:
        print("\n\nDeployment cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
