from client.github_manager import GithubObj 
from github import GithubException



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
        g = GithubObj.get_github_client()
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