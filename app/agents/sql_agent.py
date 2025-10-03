# agents/sql_agent.py (SK >= 1.37)

import json
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function, KernelFunction
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from tools.sql_tool import run_parameterized
from tools.schema_hint import get_schema_hint

SQL_SYSTEM = (
    "You are SqlAgent. Convert a natural-language question into a **single, safe, read-only SQL** query for PostgreSQL.\n"
    "Rules:\n"
    "- Only SELECT statements. Never UPDATE/INSERT/DELETE/DROP/ALTER/TRUNCATE.\n"
    "- Prefer explicit column names.\n"
    "- Use LIMIT for large outputs.\n"
    "- Use CURRENT_DATE and date arithmetic where needed.\n"
    "Return JSON: {\"sql\": \"...\", \"explanation\": \"...\"}.\n\n"
    "Schema:\n"
    "{schema}\n\n"
    "Question: {{$input}}\n"
    "JSON:"
)

def build_sql_agent(kernel: Kernel) -> KernelFunction:
    @kernel_function(
        name="execute_sql",
        description="Execute a safe read-only SQL query and return top rows."
    )
    def execute_sql(sql: str):
        lower = sql.lower()
        banned = ["update", "delete", "insert", "drop", "alter", "truncate"]
        if any(b in lower for b in banned):
            return {"error": "Unsafe statement"}
        rows = run_parameterized(sql)
        return {"rows": rows[:50]}

    prompt = SQL_SYSTEM.replace("{schema}", get_schema_hint())

    config = PromptTemplateConfig(
        template=prompt,
        name="nl2sql",
        plugin_name="sql",
        description="Convert natural language to safe SQL with explanation",
        execution_settings={
            # Use AzureChatPromptExecutionSettings for Azure OpenAI
            "azure": AzureChatPromptExecutionSettings(temperature=0.1)
        },
    )

    return kernel.add_function(
        plugin_name="sql",
        function_name="nl2sql",
        prompt_template_config=config,
        additional_functions=[execute_sql]
    )
