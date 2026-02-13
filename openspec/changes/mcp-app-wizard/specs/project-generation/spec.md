# Project Generation Spec

## Overview

Generate production-ready Prefect project structures following the PrefectHQ/flows pattern, including sophisticated prefect.yaml with YAML anchors, Dockerfiles, and supporting infrastructure.

## Requirements

### PrefectHQ/flows Structure

1. **Directory layout**
   ```
   {project-name}/
   ├── .github/
   │   └── workflows/
   │       └── deploy.yml         # Optional: GitHub Actions
   ├── .gitignore
   ├── .pre-commit-config.yaml    # Optional: Pre-commit hooks
   ├── .mise.toml                 # Optional: Tool versions
   ├── .prefectignore
   ├── README.md
   ├── pyproject.toml             # Optional: Package config
   └── deployments/
       └── {workspace}/
           ├── prefect.yaml
           └── {flow-name}/
               ├── flow.py
               ├── requirements.txt
               ├── Dockerfile       # Optional
               └── test_flow.py     # Optional
   ```

2. **Multiple workspaces support**
   - Group flows by workspace/domain
   - Separate prefect.yaml per workspace
   - Shared .gitignore at root

### prefect.yaml Generation

1. **YAML anchors for DRY config**
   ```yaml
   definitions:
     docker_build:
       - prefect.deployments.steps.run_shell_script: &git_sha
           id: get-commit-hash
           script: git rev-parse --short HEAD
           stream_output: false
       - prefect_docker.deployments.steps.build_docker_image: &docker_build
           tag: "{{ get-commit-hash.stdout }}"
           platform: linux/amd64

     docker_push:
       - prefect_docker.deployments.steps.push_docker_image: &docker_push
           tag: "{{ get-commit-hash.stdout }}"

     schedules:
       daily_2am: &daily_2am
         cron: "0 2 * * *"
         timezone: UTC

     work_pools:
       default: &default_work_pool
         name: {work-pool-name}
         job_variables:
           image: "{{ image }}"
   ```

2. **Pull step configuration**
   ```yaml
   pull:
     - prefect.deployments.steps.git_clone:
         repository: https://github.com/{org}/{repo}
         branch: main
         # access_token: "{{ prefect.blocks.secret.repo-pat }}"  # If private
   ```

3. **Deployment entries**
   ```yaml
   deployments:
     - name: {Deployment Name}
       description: |
         {Description from runbook}
       entrypoint: deployments/{workspace}/{flow-name}/flow.py:{flow_function}
       schedule: *daily_2am  # Use anchor
       parameters:
         param1: value1
       work_pool: *default_work_pool
       concurrency_limit: 1
       concurrency_options:
         collision_strategy: ENQUEUE
       build:
         - prefect.deployments.steps.run_shell_script: *git_sha
         - prefect_docker.deployments.steps.build_docker_image:
             <<: *docker_build
             dockerfile: deployments/{workspace}/{flow-name}/Dockerfile
             image_name: {registry}/deployments/{workspace}/{flow-name}
       push:
         - prefect_docker.deployments.steps.push_docker_image:
             <<: *docker_push
             image_name: {registry}/deployments/{workspace}/{flow-name}
   ```

### Dockerfile Generation

1. **Standard template**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y --no-install-recommends \
       git \
       && rm -rf /var/lib/apt/lists/*

   # Copy requirements first for caching
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy flow code
   COPY . .

   # Default command (can be overridden)
   CMD ["python", "flow.py"]
   ```

2. **Customization options**
   - Base image selection
   - System dependencies
   - Python version
   - Additional pip installs

### requirements.txt Generation

1. **Dependency detection**
   - Extract from converted flow imports
   - Include Prefect version
   - Include provider packages (prefect-aws, prefect-gcp, etc.)

2. **Version pinning**
   - Pin major.minor for stability
   - Option for exact versions
   - Option for ranges

### Supporting Files

1. **.gitignore**
   ```
   # Python
   __pycache__/
   *.py[cod]
   .venv/
   venv/

   # Prefect
   .prefect/

   # IDE
   .idea/
   .vscode/
   *.swp

   # Testing
   .pytest_cache/
   .coverage
   htmlcov/

   # Environment
   .env
   .env.local
   ```

2. **.prefectignore**
   ```
   # Ignore test files in deployment
   **/test_*.py
   **/*_test.py
   **/tests/

   # Ignore development files
   .git/
   .github/
   .vscode/
   __pycache__/
   *.pyc
   ```

3. **.pre-commit-config.yaml**
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.3.0
       hooks:
         - id: ruff
           args: [--fix]
         - id: ruff-format

     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v4.5.0
       hooks:
         - id: trailing-whitespace
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-added-large-files
   ```

4. **README.md**
   ```markdown
   # {Project Name}

   Prefect flows migrated from Airflow.

   ## Setup

   ```bash
   pip install -r requirements.txt
   ```

   ## Local Testing

   ```bash
   python deployments/{workspace}/{flow-name}/flow.py
   ```

   ## Deployment

   ```bash
   prefect deploy --all --prefect-file deployments/{workspace}/prefect.yaml
   ```

   ## Flows

   | Flow | Description | Schedule |
   |------|-------------|----------|
   | {flow-name} | {description} | {schedule} |
   ```

5. **GitHub Actions** (optional)
   ```yaml
   name: Deploy Flows

   on:
     push:
       branches: [main]
       paths:
         - 'deployments/**'

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - name: Setup Python
           uses: actions/setup-python@v5
           with:
             python-version: '3.11'

         - name: Install Prefect
           run: pip install prefect prefect-docker

         - name: Login to Prefect Cloud
           run: prefect cloud login --key ${{ secrets.PREFECT_API_KEY }}

         - name: Deploy
           run: prefect deploy --all
   ```

### ZIP Export

1. **Structure**
   - Maintain directory hierarchy
   - Include all generated files
   - Proper file permissions

2. **Implementation**
   - Use JSZip library
   - Stream download in browser
   - Fallback: concatenate files with headers

## Acceptance Criteria

- [ ] Generates PrefectHQ/flows directory structure
- [ ] prefect.yaml uses YAML anchors correctly
- [ ] Dockerfiles generated per flow
- [ ] requirements.txt has correct dependencies
- [ ] .gitignore and .prefectignore included
- [ ] README.md documents all flows
- [ ] GitHub Actions workflow valid YAML
- [ ] ZIP export maintains structure
- [ ] All files have correct content
