"""
Multi-agent team orchestration using AutoGen

Creates a team of specialized agents:
- Manager/Architect: coordinates and reviews
- Backend Engineer: implements Python/FastAPI
- Frontend Engineer: implements React/TypeScript
- Test Engineer: writes comprehensive tests
- Code Reviewer: ensures quality and completeness
"""

from autogen import AssistantAgent, GroupChat, GroupChatManager
from .config import AgentConfig
from .prompts import (
    MANAGER_SYSTEM_PROMPT,
    BACKEND_ENGINEER_SYSTEM_PROMPT,
    FRONTEND_ENGINEER_SYSTEM_PROMPT,
    TEST_ENGINEER_SYSTEM_PROMPT,
    CODE_REVIEWER_SYSTEM_PROMPT,
)


def create_manager_agent(llm_config: dict) -> AssistantAgent:
    """Create the manager/architect agent"""
    return AssistantAgent(
        name="architect",
        system_message=MANAGER_SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
    )


def create_backend_agent(llm_config: dict) -> AssistantAgent:
    """Create the backend engineer agent"""
    return AssistantAgent(
        name="backend_engineer",
        system_message=BACKEND_ENGINEER_SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
    )


def create_frontend_agent(llm_config: dict) -> AssistantAgent:
    """Create the frontend engineer agent"""
    return AssistantAgent(
        name="frontend_engineer",
        system_message=FRONTEND_ENGINEER_SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
    )


def create_test_agent(llm_config: dict) -> AssistantAgent:
    """Create the QA/test engineer agent"""
    return AssistantAgent(
        name="qa_engineer",
        system_message=TEST_ENGINEER_SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
    )


def create_reviewer_agent(llm_config: dict) -> AssistantAgent:
    """Create the code reviewer agent"""
    return AssistantAgent(
        name="code_reviewer",
        system_message=CODE_REVIEWER_SYSTEM_PROMPT,
        llm_config=llm_config,
        human_input_mode="NEVER",
        max_consecutive_auto_reply=2,
    )


class CodingTeam:
    """Manages the multi-agent coding team"""

    def __init__(self, max_rounds: int = 50):
        """
        Initialize the coding team with specialized agents

        Args:
            max_rounds: Maximum number of conversation rounds
        """
        self.max_rounds = max_rounds

        # Print engine status
        AgentConfig.print_status()

        # Get configurations for each agent
        print("Initializing agents...")
        manager_config = AgentConfig.get_manager_config().to_llm_config()
        backend_config = AgentConfig.get_backend_agent_config().to_llm_config()
        frontend_config = AgentConfig.get_frontend_agent_config().to_llm_config()
        test_config = AgentConfig.get_backend_agent_config().to_llm_config()  # Can reuse backend
        reviewer_config = AgentConfig.get_reviewer_agent_config().to_llm_config()

        # Create agents
        self.manager = create_manager_agent(manager_config)
        self.backend = create_backend_agent(backend_config)
        self.frontend = create_frontend_agent(frontend_config)
        self.test = create_test_agent(test_config)
        self.reviewer = create_reviewer_agent(reviewer_config)

        # All agents
        self.agents = [self.manager, self.backend, self.frontend, self.test, self.reviewer]

        print(f"✓ Team ready: {len(self.agents)} agents")
        print(f"  Manager:  {manager_config.get('model')}")
        print(f"  Backend:  {backend_config.get('model')}")
        print(f"  Frontend: {frontend_config.get('model')}")
        print(f"  Tests:    {test_config.get('model')}")
        print(f"  Reviewer: {reviewer_config.get('model')}")
        print()

    def start_coding_session(
        self,
        task_description: str,
        max_rounds: int | None = None,
    ) -> dict:
        """
        Start a coding session with the team

        Args:
            task_description: The project task/specification
            max_rounds: Override the default max rounds

        Returns:
            Dictionary with session results and transcript
        """
        rounds = max_rounds or self.max_rounds

        # Create group chat
        group_chat = GroupChat(
            agents=self.agents,
            messages=[],
            max_round=rounds,
            speaker_selection_method="auto",
        )

        # Create group chat manager
        manager_instance = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.manager.llm_config,
        )

        print("=" * 60)
        print("STARTING CODING SESSION")
        print("=" * 60)
        print(f"Task: {task_description[:100]}...")
        print(f"Max rounds: {rounds}")
        print("=" * 60)
        print()

        # Initiate chat
        manager_instance.initiate_chat(
            self.manager,
            message=task_description,
        )

        # Extract transcript
        transcript = group_chat.messages
        result = {
            "total_rounds": group_chat.round_num,
            "total_messages": len(transcript),
            "agents": [agent.name for agent in self.agents],
            "transcript": transcript,
        }

        return result

    def get_transcript_summary(self, result: dict) -> str:
        """Generate a summary of the coding session"""
        summary = f"""
CODING SESSION SUMMARY
======================
Total Rounds: {result['total_rounds']}
Total Messages: {result['total_messages']}
Agents Involved: {', '.join(result['agents'])}

Last 10 Messages:
"""
        for msg in result['transcript'][-10:]:
            if isinstance(msg, dict):
                summary += f"\n{msg.get('name', 'Unknown')}: {msg.get('content', '')[:200]}..."
            else:
                summary += f"\n{str(msg)[:200]}..."

        return summary


def create_team(max_rounds: int = 50) -> CodingTeam:
    """Factory function to create a coding team"""
    return CodingTeam(max_rounds=max_rounds)
