"""Development: Git, Gitea, Jenkins, GitLab Runner, Python, Node.js."""
from .base import Service, ServiceCategory


class DevelopmentServices(ServiceCategory):
    name = "Development"

    services = (
        Service("git", "Git", "Development", ("git",), (), None,
                description="VCS"),
        Service("gitea", "Gitea", "Development", ("gitea",), ("gitea",), 3000,
                ("/etc/gitea",), external_repo=True,
                description="Git service ringan"),
        Service("jenkins", "Jenkins", "Development", ("jenkins",), ("jenkins",),
                8080, ("/etc/default/jenkins", "/var/lib/jenkins"),
                external_repo=True, description="CI/CD automation"),
        Service("gitlab-runner", "GitLab Runner", "Development",
                ("gitlab-runner",), ("gitlab-runner",), None,
                ("/etc/gitlab-runner",), external_repo=True,
                description="Runner CI GitLab"),
        Service("python-env", "Python Environment", "Development",
                ("python3", "python3-pip", "python3-venv"), (), None,
                description="Python + pip + venv"),
        Service("nodejs", "Node.js", "Development", ("nodejs", "npm"), (), None,
                ("/etc/nodejs",), external_repo=True,
                description="JavaScript runtime + npm"),
    )