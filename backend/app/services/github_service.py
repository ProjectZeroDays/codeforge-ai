import os
import base64
from typing import List, Dict, Any, Optional
from github import Github, GithubException
from datetime import datetime
import asyncio


class GitHubService:
    """
    GitHub Integration Service
    Handles repository creation, file management, and Git operations
    """
    
    def __init__(self):
        self.access_token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        self._available = bool(self.access_token)
        
        if not self._available:
            print("[WARN] GitHub token not configured - GitHub features disabled")
            self.github = None
            self.user = None
        else:
            self.github = Github(self.access_token)
            self.user = self.github.get_user()
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def _check_available(self):
        if not self._available:
            raise ValueError("GitHub token not configured. Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable.")
    
    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository
        """
        self._check_available()
        try:
            repo = await asyncio.to_thread(
                self.user.create_repo,
                name=name,
                description=description,
                private=private,
                auto_init=auto_init
            )
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "created_at": repo.created_at.isoformat(),
                "private": repo.private
            }
        except GithubException as e:
            raise Exception(f"Failed to create repository: {e.data.get('message', str(e))}")
    
    async def push_files(
        self,
        repo_name: str,
        files: List[Dict[str, str]],
        commit_message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Push multiple files to a GitHub repository
        
        Args:
            repo_name: Repository name (e.g., "username/repo")
            files: List of dicts with 'path' and 'content' keys
            commit_message: Commit message
            branch: Branch name (default: "main")
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            
            # Get the current commit SHA
            ref = await asyncio.to_thread(repo.get_git_ref, f"heads/{branch}")
            commit_sha = ref.object.sha
            commit = await asyncio.to_thread(repo.get_git_commit, commit_sha)
            tree_sha = commit.tree.sha
            
            # Create blobs for all files
            element_list = []
            for file_data in files:
                # Create blob
                blob = await asyncio.to_thread(
                    repo.create_git_blob,
                    file_data['content'],
                    "utf-8"
                )
                
                element_list.append({
                    "path": file_data['path'],
                    "mode": "100644",  # Regular file
                    "type": "blob",
                    "sha": blob.sha
                })
            
            # Create tree
            tree = await asyncio.to_thread(
                repo.create_git_tree,
                element_list,
                tree_sha
            )
            
            # Create commit
            new_commit = await asyncio.to_thread(
                repo.create_git_commit,
                commit_message,
                tree,
                [commit]
            )
            
            # Update reference
            ref = await asyncio.to_thread(
                repo.get_git_ref,
                f"heads/{branch}"
            )
            await asyncio.to_thread(ref.edit, new_commit.sha)
            
            return {
                "success": True,
                "commit_sha": new_commit.sha,
                "commit_url": f"https://github.com/{repo_name}/commit/{new_commit.sha}",
                "files_pushed": len(files),
                "branch": branch
            }
        
        except GithubException as e:
            raise Exception(f"Failed to push files: {e.data.get('message', str(e))}")
    
    async def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        source_branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Create a new branch
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            source_ref = await asyncio.to_thread(
                repo.get_git_ref,
                f"heads/{source_branch}"
            )
            
            new_ref = await asyncio.to_thread(
                repo.create_git_ref,
                f"refs/heads/{branch_name}",
                source_ref.object.sha
            )
            
            return {
                "branch": branch_name,
                "sha": new_ref.object.sha,
                "created_from": source_branch
            }
        except GithubException as e:
            raise Exception(f"Failed to create branch: {e.data.get('message', str(e))}")
    
    async def create_pull_request(
        self,
        repo_name: str,
        title: str,
        head_branch: str,
        base_branch: str = "main",
        body: str = ""
    ) -> Dict[str, Any]:
        """
        Create a pull request
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            pr = await asyncio.to_thread(
                repo.create_pull,
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            return {
                "number": pr.number,
                "title": pr.title,
                "html_url": pr.html_url,
                "state": pr.state,
                "created_at": pr.created_at.isoformat()
            }
        except GithubException as e:
            raise Exception(f"Failed to create PR: {e.data.get('message', str(e))}")
    
    async def list_repositories(self) -> List[Dict[str, Any]]:
        """
        List user's repositories
        """
        self._check_available()
        try:
            repos = await asyncio.to_thread(lambda: list(self.user.get_repos()))
            
            return [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "html_url": repo.html_url,
                    "private": repo.private,
                    "created_at": repo.created_at.isoformat(),
                    "updated_at": repo.updated_at.isoformat(),
                    "language": repo.language,
                    "stargazers_count": repo.stargazers_count
                }
                for repo in repos[:50]  # Limit to 50 most recent
            ]
        except GithubException as e:
            raise Exception(f"Failed to list repos: {e.data.get('message', str(e))}")
    
    async def get_repo_status(self, repo_name: str) -> Dict[str, Any]:
        """
        Get repository status and info
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            
            # Get latest commit
            commits = await asyncio.to_thread(
                lambda: list(repo.get_commits()[:1])
            )
            latest_commit = commits[0] if commits else None
            
            # Get branches
            branches = await asyncio.to_thread(
                lambda: list(repo.get_branches())
            )
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "html_url": repo.html_url,
                "default_branch": repo.default_branch,
                "branches": [b.name for b in branches],
                "latest_commit": {
                    "sha": latest_commit.sha,
                    "message": latest_commit.commit.message,
                    "author": latest_commit.commit.author.name,
                    "date": latest_commit.commit.author.date.isoformat()
                } if latest_commit else None,
                "size": repo.size,
                "language": repo.language
            }
        except GithubException as e:
            raise Exception(f"Failed to get repo status: {e.data.get('message', str(e))}")
    
    async def get_file_content(
        self,
        repo_name: str,
        file_path: str,
        branch: str = "main"
    ) -> str:
        """
        Get file content from repository
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            file_content = await asyncio.to_thread(
                repo.get_contents,
                file_path,
                ref=branch
            )
            
            # Decode content
            if isinstance(file_content, list):
                raise Exception(f"{file_path} is a directory")
            
            return base64.b64decode(file_content.content).decode('utf-8')
        except GithubException as e:
            raise Exception(f"Failed to get file: {e.data.get('message', str(e))}")
    
    async def delete_file(
        self,
        repo_name: str,
        file_path: str,
        commit_message: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Delete a file from repository
        """
        self._check_available()
        try:
            repo = self.github.get_repo(repo_name)
            file = await asyncio.to_thread(
                repo.get_contents,
                file_path,
                ref=branch
            )
            
            result = await asyncio.to_thread(
                repo.delete_file,
                file_path,
                commit_message,
                file.sha,
                branch=branch
            )
            
            return {
                "success": True,
                "commit_sha": result['commit'].sha,
                "message": f"Deleted {file_path}"
            }
        except GithubException as e:
            raise Exception(f"Failed to delete file: {e.data.get('message', str(e))}")