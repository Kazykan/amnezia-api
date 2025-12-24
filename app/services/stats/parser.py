def parse_wg_dump(raw: str):
    peers = []
    for line in raw.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 7:
            continue

        peer = {
            "public_key": parts[0],
            "endpoint": parts[2],
            "allowed_ips": parts[3],
            "latest_handshake": int(parts[4]),
            "rx_bytes": int(parts[5]),
            "tx_bytes": int(parts[6]),
        }
        peers.append(peer)

    return peers
