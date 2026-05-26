from crewai import Agent, LLM
from .config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from .tools import write_draft, write_review, write_proposal


def _create_llm() -> LLM:
    return LLM(
        model=f"openai/{LLM_MODEL}",
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        max_tokens=32000,
    )


def create_writer() -> Agent:
    return Agent(
        role="Novel Chapter Writer",
        goal="Write a compelling chapter that advances the story based on the provided context (canon, ledgers, arc_contract, arc_working_state)",
        backstory="You are a skilled fiction writer who crafts engaging chapters while maintaining strict consistency with the established story facts.",
        tools=[write_draft],
        llm=_create_llm(),
        verbose=True,
    )


def create_auditor() -> Agent:
    return Agent(
        role="Continuity Auditor",
        goal="Review the chapter draft for consistency with canon, ledgers, and arc_contract. Report any POV violations, timeline contradictions, or character inconsistencies.",
        backstory="You are a meticulous continuity checker who catches every inconsistency between new chapters and established story facts.",
        tools=[write_review],
        llm=_create_llm(),
        verbose=True,
    )


def create_extractor() -> Agent:
    return Agent(
        role="Knowledge Extractor",
        goal="Extract narrative facts from the chapter and review, producing structured JSON proposals for timeline events, character knowledge, and foreshadowing updates.",
        backstory="You identify narrative facts that need to be recorded in the story ledgers and produce well-structured proposals with source citations and evidence.",
        tools=[write_proposal],
        llm=_create_llm(),
        verbose=True,
    )
