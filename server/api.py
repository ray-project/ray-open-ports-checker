from pydantic import BaseModel, validator


class OpenPortCheckRequest(BaseModel):
    ports: list[int]

    @validator("ports")
    def validate_ports(cls, ports):
        if len(ports) == 0:
            raise ValueError("Ports list cannot be empty")

        invalid_ports = [port for port in ports if not 0 <= port <= 65535]

        if invalid_ports:
            raise ValueError(f"Ports {invalid_ports} are not valid port numbers")

        return ports


class OpenPortCheckResponse(BaseModel):
    open_ports: list[int]
    checked_ports: list[int]
