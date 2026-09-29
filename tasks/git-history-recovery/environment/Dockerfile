FROM python:3.11-slim
WORKDIR /workspace
COPY . /workspace
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/* && git init repo && cd repo && git config user.name 'AgentForge' && git config user.email 'agentforge@example.com' && printf 'baseline\n' > app.txt && git add app.txt && git commit -m 'baseline' && printf 'critical recovery data\n' > recovery.txt && git add recovery.txt && git commit -m 'recover-critical-data' && git reset --hard HEAD~1 && echo 'repository intentionally left in a broken state' > /workspace/state.txt
CMD ["bash"]
