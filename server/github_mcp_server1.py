
import sys
from pathlib import Path
from github import Github, GithubException, Auth
from typing import Optional


# Add parent directory to sys.path for modular imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.server_manager import ServerManager
from client.github_manager import GithubObj 
from config.settings import settings
# 1. Initialize Manager
manager = ServerManager(server_name=settings.GITHUB_SERVER_NAME)


# 2. Create Server Instance
# The 'instructions' help the LLM understand when to use this specific server
mcp = manager.server_implementation(
    instructions="GitHub tools for AI agents - Create, Read, Delete repos & more"
)

g = GithubObj.get_github_client()


@mcp.tool()
async def create_repository(
    name: str,
    description: str = '',
    private: bool = False,
    auto_init: bool = True
) -> dict:
    """
    Create a new GitHub repository (asynchronous interface).

    Args:
        name: Repository name (no spaces, use hyphens)
        description: Short description of the repo
        private: True for private, False for public
        auto_init: Initialize with README.md + .gitignore + license (if selected)

    Returns:
        Dict with status, repo details or error message
    """
    try:
        global g
        user = g.get_user()
        repo = user.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=auto_init
        )
        return {
            "status": "success",
            "name": repo.full_name,
            "url": repo.html_url,
            "private": repo.private,
            "created_at": str(repo.created_at),
            "ssh_url": repo.ssh_url,
            "clone_url": repo.clone_url
        }
    except GithubException as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def delete_repository(
    repo_name: str
) -> dict:
    """
    Delete a GitHub repository permanently (asynchronous interface).

    Args:
        repo_name: Full repo name as 'username/repo-name'
                   OR just 'repo-name' (assumes authenticated user's repo)

    Returns:
        Dict with status and confirmation or error message
    """
    try:
        global g
        if '/' in repo_name:
            repo = g.get_repo(repo_name)
        else:
            user = g.get_user()
            repo = g.get_repo(f'{user.login}/{repo_name}')

        full_name = repo.full_name
        repo.delete()
        return {
            "status": "success",
            "deleted": full_name,
            "message": "Repository permanently deleted"
        }
    except GithubException as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_repositories(
    username: Optional[str] = None,
    repo_type: str = 'owner',
    limit: int = 20
) -> dict:
    """
    List repositories for a user (asynchronous interface).

    Args:
        username: GitHub username (None = authenticated user)
        repo_type: 'owner', 'all', 'member', 'public', 'private'
        limit: Max number of repos to return (default 20)

    Returns:
        Dict with status, count, and list of repo summaries
    """
    try:
        global g

        if username:
            user = g.get_user(username)
            repos = user.get_repos()
        else:
            user = g.get_user()
            repos = user.get_repos(type=repo_type)

        repo_list = []
        for i, repo in enumerate(repos):
            if i >= limit:
                break
            repo_list.append({
                "name": repo.full_name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "private": repo.private,
                "url": repo.html_url,
                "created_at": str(repo.created_at.date())
            })

        return {
            "status": "success",
            "count": len(repo_list),
            "repos": repo_list
        }
    except GithubException as e:
        return {"status": "error", "message": str(e)}
    
if __name__ == '__main__':
    mcp.run(transport='stdio')
