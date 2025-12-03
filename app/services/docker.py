import docker  # type: ignore

client = docker.from_env()


def exec_in_container(
    container_name: str, command: str, input_data: str | None = None
) -> str:
    """
    Выполнить команду внутри Docker-контейнера с поддержкой stdin (input_data)
    """
    container = client.containers.get(container_name)

    # exec_run умеет принимать stdin через параметр 'stdin=True'
    exec_id = client.api.exec_create(container.id, cmd=command, stdin=True, tty=False)[
        "Id"
    ]

    sock = client.api.exec_start(exec_id, detach=False, stream=True, socket=True)
    if input_data:
        sock._sock.send(input_data.encode())
        sock._sock.shutdown(1)  # закрыть stdin

    output = b""
    for chunk in sock:
        output += chunk

    resp = client.api.exec_inspect(exec_id)
    if resp["ExitCode"] != 0:
        raise Exception(output.decode().strip())

    return output.decode("utf-8", errors="ignore").strip()
