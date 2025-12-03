import re


def parse_wg_show(output: str) -> dict:
    peer_match = re.search(r"peer:\s*(\S+)", output)
    endpoint_match = re.search(r"endpoint:\s*(\S+)", output)
    allowed_ips_match = re.search(r"allowed ips:\s*(\S+)", output)
    handshake_match = re.search(r"latest handshake:\s*(.+)", output)
    transfer_match = re.search(r"transfer:\s*(.+)", output)

    return {
        "peer": peer_match.group(1) if peer_match else None,
        "endpoint": endpoint_match.group(1) if endpoint_match else None,
        "allowed_ips": allowed_ips_match.group(1) if allowed_ips_match else None,
        "latest_handshake": (
            handshake_match.group(1).strip() if handshake_match else None
        ),
        "transfer": transfer_match.group(1).strip() if transfer_match else None,
    }
