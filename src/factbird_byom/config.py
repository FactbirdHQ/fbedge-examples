from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClientConfig:
    region: str
    account_id: str

    def __post_init__(self) -> None:
        if not self.region:
            raise ValueError("region is required")
        if not self.account_id:
            raise ValueError("account_id is required")

    @property
    def bucket(self) -> str:
        """The BYOM S3 bucket name, derived by Factbird convention."""
        return f"{self.account_id}-{self.region}-byom"
