from github import Github, Auth
from config.settings import settings

class GitHubMCPServer:
    def __init__(self):
        self._github_client: Github | None = None

    def get_github_client(self) -> Github:
        if self._github_client is not None:
            return self._github_client

        token = settings.GITHUB_TOKEN
        if not token:
            raise ValueError("GITHUB_TOKEN not set in environment")

        self._github_client = Github(auth=Auth.Token(token))
        return self._github_client
    
GithubObj = GitHubMCPServer()