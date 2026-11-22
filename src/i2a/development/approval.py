from i2a.development.proposal import DevelopmentProposal


class ProposalApproval:
    """Manages user approval decisions for development proposals."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    def __init__(self, proposal: DevelopmentProposal) -> None:
        if not isinstance(proposal, DevelopmentProposal):
            raise TypeError(
                "Expected a DevelopmentProposal object."
            )

        self.proposal = proposal
        self.status = self.PENDING

    def approve(self) -> None:
        """Approve a pending development proposal."""

        if self.status != self.PENDING:
            raise ValueError(
                "Only pending proposals can be approved."
            )

        self.status = self.APPROVED

    def reject(self) -> None:
        """Reject a pending development proposal."""

        if self.status != self.PENDING:
            raise ValueError(
                "Only pending proposals can be rejected."
            )

        self.status = self.REJECTED

    def to_dict(self) -> dict:
        """Return the proposal and its current approval status."""

        return {
            "status": self.status,
            "proposal": self.proposal.to_dict(),
        }
