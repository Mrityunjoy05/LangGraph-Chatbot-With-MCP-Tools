from client.github_manager import GithubObj 
from github import GithubException
from typing import Optional


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
        g = GithubObj.get_github_client()

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