from client.github_manager import GithubObj 
from github import GithubException




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
        g = GithubObj.get_github_client()
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