import os
import hashlib
from typing import Tuple

def compute_file_sha256(file_path: str, short: bool = True) -> str:
    """
    Computes cryptographic SHA-256 hash of a file on local disk.
    If short is True, formats as 'sha256:<first_16_chars>' matching OutLiners_SIH.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found on disk: {file_path}")

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)

    full_hex = hasher.hexdigest()
    if short:
        return f"sha256:{full_hex[:16]}"
    return full_hex

def verify_evidence_integrity(file_path: str, expected_hash: str) -> Tuple[bool, str, str]:
    """
    Verifies that the file on disk matches the expected SHA-256 recorded in the database.
    Returns: (is_valid, computed_hash, expected_hash)
    """
    if not os.path.exists(file_path):
        return False, "FILE_NOT_FOUND", expected_hash

    # OutLiners_SIH stores either 'sha256:<16_chars>' or full hex
    is_short = expected_hash.startswith("sha256:") and len(expected_hash) <= 24
    computed = compute_file_sha256(file_path, short=is_short)

    is_valid = (computed.lower() == expected_hash.lower())
    return is_valid, computed, expected_hash
