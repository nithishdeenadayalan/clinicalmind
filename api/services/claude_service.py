import anthropic
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path("C:/full time/clinicalmind/.env"))

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    env_file = Path("C:/full time/clinicalmind/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY"):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

client = anthropic.Anthropic(api_key=api_key)

SYSTEM_PROMPT = "You are ClinicalMind, an expert AI assistant for clinical trial intelligence. You help pharmaceutical researchers, CROs, and medical professionals analyze clinical trial data. Write in plain professional prose only. Do not use markdown, asterisks, pound signs, headers, bullet points, tables, or any special symbols. Cite NCT IDs when referencing trials. Highlight phase, status, enrollment size, and sponsor when relevant. Keep responses concise and factual."


def ask_claude(query: str, trial_context: list) -> str:
    context_text = ""
    for i, trial in enumerate(trial_context[:8], 1):
        context_text += f"Trial {i}: NCT ID {trial.get('nct_id')}, Title: {trial.get('title')}, Phase: {trial.get('phase_clean')}, Status: {trial.get('status_clean')}, Conditions: {trial.get('conditions')}, Interventions: {trial.get('interventions')}, Sponsor: {trial.get('sponsor')} ({trial.get('sponsor_class')}), Enrollment: {trial.get('enrollment')}. Summary: {trial.get('rag_text', '')[:200]}. "

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Question: {query}. Context: {context_text}"
        }]
    )
    return message.content[0].text