"""Use cases on top of plymotion.core, independent of any UI or transport.

Long-running operations take a Reporter so the caller (the job manager, a
test) decides how progress, log lines and cancellation are surfaced.
"""
