import subprocess


def exec_in_container(
    container_name: str, command: str, input_data: str | None = None
) -> str:
    """
    Выполнить команду внутри Docker-контейнера
    """
    full_cmd = ["docker", "exec", "-i", container_name] + command.split()
    result = subprocess.run(full_cmd, input=input_data, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(result.stderr.strip())
    return result.stdout.strip()
