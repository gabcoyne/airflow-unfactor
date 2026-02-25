---
name: Prefect Documentation Context
colin:
  output:
    format: json
---

# Prefect Context for Migration

This document compiles current Prefect documentation relevant to Airflow migration.

## Flows

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize the key concepts of Prefect flows for someone migrating from Airflow DAGs.
Include: @flow decorator, parameters, return values, subflows, state hooks, logging.
Be concise — bullet points with code snippets. Max 500 words.
{% endllm %}

## Tasks

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect task concepts for someone migrating from Airflow operators.
Include: @task decorator, retries, caching, concurrency, .map(), .submit(), result serialization.
Be concise — bullet points with code snippets. Max 500 words.
{% endllm %}

## Blocks

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect blocks for someone migrating from Airflow connections.
Include: what blocks are, common block types (credentials, storage, webhooks), how to create/load/use them.
Be concise — bullet points with code snippets. Max 400 words.
{% endllm %}

## Deployments

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect deployments for someone migrating from Airflow DAG scheduling.
Include: prefect.yaml, work pools, workers, schedules, parameters, serve vs deploy.
Be concise — bullet points with code snippets. Max 500 words.
{% endllm %}

## Work Pools

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect work pools for someone migrating from Airflow executors and pools.
Include: pool types (process, docker, kubernetes, ECS), workers, concurrency, infrastructure.
Be concise — bullet points. Max 300 words.
{% endllm %}

## Events and Automations

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect events and automations for someone migrating from Airflow sensors and callbacks.
Include: emit_event, automation triggers, actions, how to replace sensors with event-driven patterns.
Be concise — bullet points with code snippets. Max 400 words.
{% endllm %}

## Variables and Secrets

{% llm model="anthropic:claude-haiku-4-5" %}
Summarize Prefect variables and secrets for someone migrating from Airflow Variables.
Include: Variable.get/set, Secret blocks, environment variables in deployments.
Be concise — bullet points with code snippets. Max 300 words.
{% endllm %}
