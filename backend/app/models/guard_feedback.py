"""
GuardFeedback model — stores user-flagged false positives / false negatives
from the LLM Guard scan endpoint.

Each row represents one user correction:
  - false_positive : Guard said "block" but the prompt was actually benign
  - false_negative : Guard said "allow" but the prompt was actually malicious

These rows are the input to the continual-learning pipeline:
  backend/scripts/export_guard_feedback.py exports them as prompts.csv rows
  so the Guard classifier can be retrained on real-world mistakes.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class GuardFeedback(Base):
    __tablename__ = "guard_feedback"

    id = Column(Integer, primary_key=True, index=True)

    # The user who flagged the decision
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # The original prompt that was scanned
    prompt = Column(Text, nullable=False)

    # What the Guard decided
    guard_decision = Column(String(20), nullable=False)   # "allow" | "sanitize" | "block"

    # What the user says the correct label is
    correct_label = Column(String(20), nullable=False)    # "benign" | "malicious"

    # Feedback type derived from the above two fields (for convenience)
    # false_positive: guard=block, correct=benign
    # false_negative: guard=allow, correct=malicious
    feedback_type = Column(String(20), nullable=False)    # "false_positive" | "false_negative" | "correct"

    # Optional free-text note from the user
    note = Column(Text, nullable=True)

    # Whether this row has been exported to prompts.csv already
    exported = Column(String(5), default="false")         # "true" | "false"

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
