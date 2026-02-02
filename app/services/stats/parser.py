def parse_wg_dump(raw: str):
    peers = []
    lines = raw.splitlines()

    for line in lines:
        parts = line.split("\t")

        # В дампе AmneziaWG:
        # Строка интерфейса начинается с PrivateKey (или его отсутствия)
        # Строка пира начинается с PublicKey.
        # Нам нужны только те строки, где 8+ колонок (это пиры)
        if len(parts) < 8:
            continue

        try:
            # Индексы в дампе AWG (версия с обфускацией):
            # 0: public_key
            # 1: preshared_key
            # 2: endpoint (может быть (null))
            # 3: allowed_ips
            # 4: latest_handshake (unix timestamp)
            # 5: rx_bytes
            # 6: tx_bytes
            # 7: persistent_keepalive

            peer = {
                "public_key": parts[0],
                "endpoint": parts[2] if parts[2] != "(null)" else None,
                "allowed_ips": parts[3],
                "latest_handshake": int(parts[4]) if parts[4] != "0" else 0,
                "rx_bytes": int(parts[5]),
                "tx_bytes": int(parts[6]),
            }
            peers.append(peer)
        except (ValueError, IndexError) as e:
            print(f"Ошибка парсинга строки: {e}")
            continue

    return peers
