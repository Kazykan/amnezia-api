import subprocess


def run_cmd(cmd: str):
    """Выполняет команду в shell и выбрасывает исключение при ошибке."""
    subprocess.run(cmd, shell=True, check=True)


def block_ip(ip: str):
    """
    Блокирует IP на уровне Linux firewall.
    Блокировка действует ДО Docker, трафик не попадёт в контейнер.
    """
    # Проверяем, есть ли уже правило
    check_cmd = f"iptables -C INPUT -s {ip} -j DROP"
    try:
        run_cmd(check_cmd)
        print(f"⚠️ IP {ip} уже заблокирован.")
        return
    except subprocess.CalledProcessError:
        pass  # правила нет — продолжаем

    print(f"⛔ Блокирую IP {ip}...")

    run_cmd(f"iptables -A INPUT -s {ip} -j DROP")
    run_cmd(f"iptables -A FORWARD -s {ip} -j DROP")

    print(f"⛔ IP {ip} успешно заблокирован.")


def unblock_ip(ip: str):
    """
    Разблокирует IP на уровне Linux firewall.
    """
    print(f"🔓 Разблокирую IP {ip}...")

    # Удаляем правила, если они есть
    try:
        run_cmd(f"iptables -D INPUT -s {ip} -j DROP")
    except subprocess.CalledProcessError:
        pass

    try:
        run_cmd(f"iptables -D FORWARD -s {ip} -j DROP")
    except subprocess.CalledProcessError:
        pass

    print(f"🔓 IP {ip} успешно разблокирован.")
