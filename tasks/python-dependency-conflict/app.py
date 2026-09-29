from pydantic import BaseModel, TypeAdapter


class ServiceConfig(BaseModel):
    name: str = "agentforge"


if __name__ == "__main__":
    adapter = TypeAdapter(ServiceConfig)
    config = adapter.validate_python({"name": "agentforge"})
    print({"status": "ok", "name": config.name})
