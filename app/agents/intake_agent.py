# agents/intake_agent.py (SK >= 1.37)

from semantic_kernel import Kernel
from semantic_kernel.prompt_template import PromptTemplateConfig
from semantic_kernel.functions import KernelFunction
# Import the Azure-specific execution settings class
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings

SYSTEM = (
    "You are IntakeAgent. Normalize a raw insurance claim note.\n"
    "Extract: incident_type, key_entities, location (if any), date_of_loss (if present), "
    "concise_summary (1-2 sentences).\n"
    "Respond ONLY with a JSON object containing those keys (no code fences or extra text)."
)

def build_intake_agent(kernel: Kernel) -> KernelFunction:
    prompt = SYSTEM + "\nUser note:\n{{$input}}\nJSON:"

    # Build the prompt template with AzureChatPromptExecutionSettings
    config = PromptTemplateConfig(
        template=prompt,
        name="normalize",
        plugin_name="intake",
        description="Normalize a raw insurance claim note into structured JSON",
        execution_settings={
            # The key ("azure") must match your service_id for AzureChatCompletion
            "azure": AzureChatPromptExecutionSettings(temperature=0.2)
        },
    )

    # Register the agent function with the kernel
    return kernel.add_function(
        plugin_name="intake",
        function_name="normalize",
        prompt_template_config=config
    )
