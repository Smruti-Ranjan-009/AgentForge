from pydantic import BaseModel, ConfigDict

class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = "agentforge"

if __name__ == "__main__":
    config = ServiceConfig(name="agentforge")
    print({"status": "ok", "name": config.name})
