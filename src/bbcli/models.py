from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PullRequest:
    id: int
    title: str
    description: str
    state: str
    author: str
    source_branch: str
    destination_branch: str
    comment_count: int
    created_on: str
    updated_on: str
    url: str

    @classmethod
    def from_api(cls, data: dict) -> PullRequest:
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description") or "",
            state=data["state"],
            author=data["author"]["display_name"],
            source_branch=data["source"]["branch"]["name"],
            destination_branch=data["destination"]["branch"]["name"],
            comment_count=data.get("comment_count", 0),
            created_on=data["created_on"],
            updated_on=data["updated_on"],
            url=data["links"]["html"]["href"],
        )


@dataclass
class InlineContext:
    path: str
    from_line: int | None = None
    to_line: int | None = None


@dataclass
class Comment:
    id: int
    content: str
    user: str
    created_on: str
    resolved: bool = False
    inline: InlineContext | None = None
    parent_id: int | None = None
    children: list[Comment] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> Comment:
        inline = None
        if data.get("inline"):
            inline = InlineContext(
                path=data["inline"]["path"],
                from_line=data["inline"].get("from"),
                to_line=data["inline"].get("to"),
            )
        parent_id = None
        if data.get("parent"):
            parent_id = data["parent"]["id"]

        resolution = data.get("resolution")
        resolved = resolution is not None

        return cls(
            id=data["id"],
            content=data["content"]["raw"],
            user=data["user"]["display_name"],
            created_on=data["created_on"],
            resolved=resolved,
            inline=inline,
            parent_id=parent_id,
        )


@dataclass
class DiffStat:
    path: str
    status: str
    lines_added: int
    lines_removed: int

    @classmethod
    def from_api(cls, data: dict) -> DiffStat:
        return cls(
            path=data.get("new", {}).get("path") or data.get("old", {}).get("path", ""),
            status=data["status"],
            lines_added=data.get("lines_added", 0),
            lines_removed=data.get("lines_removed", 0),
        )
