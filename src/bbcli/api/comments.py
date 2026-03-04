from __future__ import annotations

from bbcli.client import BitbucketClient
from bbcli.models import Comment


def list_comments(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
) -> list[Comment]:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments"
    items = client.paginate(path)
    return [Comment.from_api(item) for item in items]


def create_comment(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
    body: str,
    inline: dict | None = None,
    parent_id: int | None = None,
) -> Comment:
    """Create a comment on a PR.

    Args:
        inline: dict with keys "path", and optionally "to" (line number).
        parent_id: ID of the parent comment for replies.
    """
    payload: dict = {"content": {"raw": body}}
    if inline:
        payload["inline"] = inline
    if parent_id:
        payload["parent"] = {"id": parent_id}

    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments"
    resp = client.post(path, json=payload)
    return Comment.from_api(resp.json())


def resolve_comment(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
    comment_id: int,
) -> None:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments/{comment_id}/resolve"
    client.put(path)


def unresolve_comment(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
    comment_id: int,
) -> None:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments/{comment_id}/resolve"
    client.delete(path)


def delete_comment(
    client: BitbucketClient,
    workspace: str,
    repo: str,
    pr_id: int,
    comment_id: int,
) -> None:
    path = f"/repositories/{workspace}/{repo}/pullrequests/{pr_id}/comments/{comment_id}"
    client.delete(path)
