from __future__ import annotations

from bbcli.client import BitbucketClient
from bbcli.models import DiffStat, PullRequest


def list_prs(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    state: str = "OPEN",
    sort: str = "-updated_on",
    limit: int = 25,
) -> list[PullRequest]:
    path = f"/repositories/{workspace}/{repo}/pullrequests"
    params = {"state": state, "sort": sort}
    items = client.paginate(path, params=params, limit=limit)
    return [PullRequest.from_api(item) for item in items]


def get_pr(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
) -> PullRequest:
    resp = client.get(f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}")
    return PullRequest.from_api(resp.json())


def get_diff(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
) -> str:
    resp = client.get(f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/diff")
    return resp.text


def create_pr(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    title: str,
    source_branch: str,
    destination_branch: str,
    description: str = "",
    close_source_branch: bool = False,
    reviewers: list[str] | None = None,
) -> PullRequest:
    path = f"/repositories/{workspace}/{repo}/pullrequests"
    body: dict = {
        "title": title,
        "source": {"branch": {"name": source_branch}},
        "destination": {"branch": {"name": destination_branch}},
        "close_source_branch": close_source_branch,
    }
    if description:
        body["description"] = description
    if reviewers:
        body["reviewers"] = [
            {"uuid": r} if r.startswith("{") else {"username": r}
            for r in reviewers
        ]
    resp = client.post(path, json=body)
    return PullRequest.from_api(resp.json())


def approve_pr(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
) -> None:
    client.post(f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/approve")


def merge_pr(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
    merge_strategy: str | None = None,
    close_source_branch: bool = False,
) -> PullRequest:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/merge"
    body: dict = {"close_source_branch": close_source_branch}
    if merge_strategy:
        body["merge_strategy"] = merge_strategy
    resp = client.post(path, json=body)
    return PullRequest.from_api(resp.json())


def get_diffstat(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
) -> list[DiffStat]:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/diffstat"
    items = client.paginate(path)
    return [DiffStat.from_api(item) for item in items]
