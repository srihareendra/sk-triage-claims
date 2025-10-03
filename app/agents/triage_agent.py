# agents/triage_agent.py  (SK >= 1.37)

from semantic_kernel import Kernel
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.functions import KernelFunction
# Use Azure-specific execution settings
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings

SYSTEM = (
    "You are TriageAgent for an insurer. Score severity and fraud_risk based on summary and context.\n"
    "- severity ∈ {LOW, MEDIUM, HIGH}\n"
    "- fraud_risk ∈ [0,1]\n"
    "- route_to ∈ {OPERATIONS, SIU}\n"
    "Explain your reasoning in 'rationale'.\n"
    "Return JSON with keys: severity, fraud_risk, route_to, rationale.\n"
    "Be conservative; route to SIU if fraud_risk ≥ 0.65."
)

def build_triage_agent(kernel: Kernel) -> KernelFunction:
    prompt = SYSTEM + "\nSummary:\n{{$summary}}\nContext:\n{{$context}}\nJSON:"

    # Create a PromptTemplateConfig and specify Azure settings via AzureChatPromptExecutionSettings.
    config = PromptTemplateConfig(
        template=prompt,
        name="score",
        plugin_name="triage",
        description="Score insurance claims for severity and fraud risk",
        execution_settings={
            # This key must match the service_id ("azure") you used when adding AzureChatCompletion to the kernel
            "azure": AzureChatPromptExecutionSettings(temperature=0.1)
        },
    )

    # Register the function with the kernel
    return kernel.add_function(
        plugin_name="triage",
        function_name="score",
        prompt_template_config=config
    )
