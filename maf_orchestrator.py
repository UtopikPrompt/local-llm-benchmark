from openai import AsyncOpenAI
from agent_framework.orchestrations import SequentialBuilder
from agent_framework import Agent, Message
import os
import re
import asyncio
import subprocess
import urllib.request
from pathlib import Path
from typing import List, Dict, Any
from agent_framework_openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()  # load variables from .env in the current working directory

# Core Microsoft Agent Framework imports

# Open-AI compatible backend client for local Ollama orchestration

# =====================================================================
# 1. Pipeline & Workspace Configurations (Absolute Path Anchoring)
# =====================================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_PROJECT_PATH = os.getenv("TARGET_PROJECT_PATH", ROOT_DIR)
TEST_COMMAND = os.getenv("TEST_COMMAND", "cd engine && pytest tests/")
PLAN_FILE_PATH = os.path.join(ROOT_DIR, "./docs/plan.md")


def normalize_llm_base_url(raw_url: str) -> str:
    """Accept both root Ollama URLs and OpenAI-style /v1 endpoints."""
    normalized = (raw_url or "http://localhost:11434").strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


LLM_BASE_URL = normalize_llm_base_url(
    os.getenv("LLM_BASE_URL", "http://localhost:11434"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL_DEFAULT = os.getenv(
    "LLM_MODEL_DEFAULT", "Ornith-1.5-35B-Q4_K_M:128K")
MAX_HEALING_ITERATIONS = max(
    1, int(os.getenv("MAX_HEALING_ITERATIONS", "3")))

FILE_BLOCK_PATTERNS = [
    r"---\s*FILE:\s*([^\n]+?)\s*---\s*\n(.*?)\n\s*---\s*END FILE\s*---",
    r"FILE\s*:\s*([^\n]+?)\s*\n(.*?)\n\s*END FILE\s*",
    r"```(?:[A-Za-z0-9_+-]+)?\s*---\s*FILE:\s*([^\n]+?)\s*---\s*\n(.*?)\n\s*---\s*END FILE\s*---\s*```",
]


def extract_text_payload(payload: Any) -> str:
    """Best-effort extraction of plain text from nested agent payloads."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("text", "content", "message", "output"):
            if key in payload and payload[key]:
                return extract_text_payload(payload[key])
        for value in payload.values():
            extracted = extract_text_payload(value)
            if extracted:
                return extracted
        return ""
    if isinstance(payload, (list, tuple)):
        parts = []
        for item in payload:
            extracted = extract_text_payload(item)
            if extracted:
                parts.append(extracted)
        return "\n".join(parts)
    if hasattr(payload, "text") and payload.text:
        return str(payload.text)
    if hasattr(payload, "content") and payload.content:
        return str(payload.content)
    return str(payload)


def strip_outer_code_fences(text: str) -> str:
    """Remove a single outer markdown fence pair from text."""
    if not text:
        return text
    stripped = text.strip()
    stripped = re.sub(r"^```(?:[A-Za-z0-9_+-]+)?\s*\n", "", stripped)
    stripped = re.sub(r"\n```\s*$", "", stripped)
    return stripped


def count_file_blocks(text: str) -> int:
    """Count how many file blocks are present in a payload."""
    if not text:
        return 0
    normalized = strip_outer_code_fences(text)
    for pattern in FILE_BLOCK_PATTERNS:
        matches = re.findall(pattern, normalized, re.DOTALL)
        if matches:
            return len(matches)
    return 0


def choose_best_file_block_payload(candidates: List[str]) -> str:
    """Pick the payload with the highest number of valid file blocks."""
    ranked = []
    for candidate in candidates:
        if not candidate:
            continue
        block_count = count_file_blocks(candidate)
        ranked.append((block_count, len(candidate), candidate))
    if not ranked:
        return ""
    ranked.sort(reverse=True)
    best_blocks, _, best_text = ranked[0]
    if best_blocks <= 0:
        return ""
    return best_text


def commit_all_changes(repo_path: str, message: str) -> None:
    """Create a git commit only when the working tree has content to commit."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return

        git_root = result.stdout.strip()
        subprocess.run(["git", "add", "."], cwd=git_root, check=False)
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if diff_check.returncode == 0:
            return

        subprocess.run(["git", "commit", "-m", message],
                       cwd=git_root, check=False)
    except Exception:
        return


def llm_backend_available(url: str, timeout: float = 2.0) -> bool:
    """Return True when the configured OpenAI-compatible endpoint is reachable."""
    try:
        probe_root = url.rstrip("/")
        if probe_root.endswith("/v1"):
            probe_root = probe_root[:-3]
        probe = f"{probe_root}/api/tags"
        with urllib.request.urlopen(probe, timeout=timeout) as response:
            return response.status < 500
    except Exception:
        return False

# =====================================================================
# 2. Automated Smart Plan Parser
# =====================================================================


class MarkdownPlanParser:
    @staticmethod
    def _iter_slice_sections(content: str):
        sections = re.split(
            r'(?=\n##\s+(?:\[[ xX]\]\s+)?Slice\s+\d+)', content)
        for section in sections:
            if "Slice" in section and "##" in section:
                yield section

    @staticmethod
    def mark_slice_complete(file_path: str, slice_num: int) -> None:
        """Update the checklist state for a slice in the markdown plan."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        old_pattern = rf"(?m)^(##\s+)(?:\[[ xX]\]\s+)?(Slice\s+{slice_num}\s+—)"
        new_pattern = r"\1[x] \2"
        new_content = re.sub(old_pattern, new_pattern, content)

        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

    @staticmethod
    def get_pending_slices(file_path: str) -> List[Dict]:
        """
        Read only unchecked slices from the markdown plan so completed work is not reprocessed.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Could not find plan file at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        completed_slices = set()
        for line in content.splitlines():
            header_match = re.search(
                r'^\s*##\s*(?:\[(?P<state>[xX ])\]\s*)?Slice\s+(?P<num>\d+)',
                line,
            )
            if header_match and header_match.group('state') and header_match.group('state').lower() == 'x':
                completed_slices.add(int(header_match.group('num')))

            checkbox_match = re.search(r'\[[xX]\].*?\b(\d+)\b', line)
            if checkbox_match and not header_match:
                completed_slices.add(int(checkbox_match.group(1)))

        pending_slices = []
        for section in MarkdownPlanParser._iter_slice_sections(content):
            title_match = re.search(
                r'##\s*(?:\[[ xX]\]\s+)?(Slice\s+(\d+)\s+—\s+([^\n]+))',
                section,
            )
            if title_match:
                slice_num = int(title_match.group(2))
                slice_name = title_match.group(3)
                if slice_num in completed_slices:
                    print(
                        f"ℹ️  Map Parser: Skipping completed Slice {slice_num} — {slice_name}")
                    continue
                pending_slices.append({
                    "number": slice_num,
                    "name": slice_name,
                    "markdown_content": section.strip()
                })

        return pending_slices


# =====================================================================
# 3. Native OS Tool Integrations
# =====================================================================


class LocalWorkspaceTools:
    @staticmethod
    def write_files_from_markdown(llm_output: str):
        """Write file blocks from model output into the target workspace."""
        if not llm_output or not isinstance(llm_output, str):
            return "Warning: No file blocks found in the agent output."

        text = strip_outer_code_fences(llm_output)
        matches = []
        for pattern in FILE_BLOCK_PATTERNS:
            found = re.findall(pattern, text, re.DOTALL)
            if found:
                matches.extend(found)
                break

        if not matches:
            return "Warning: No clean file structural syntax blocks matched or generated."

        base_root = Path(TARGET_PROJECT_PATH).resolve()
        report = []

        for filepath, content in matches:
            clean_filepath = filepath.strip().strip("`")
            relative_path = os.path.normpath(clean_filepath)
            if relative_path.startswith("..") or os.path.isabs(relative_path):
                report.append(f"Skipped unsafe path: {clean_filepath}")
                continue

            sanitized_content = strip_outer_code_fences(content.strip())
            sanitized_content = sanitized_content.strip()

            true_path = (base_root / relative_path).resolve()
            if base_root not in true_path.parents and true_path != base_root:
                report.append(f"Skipped escaped path: {clean_filepath}")
                continue

            true_path.parent.mkdir(parents=True, exist_ok=True)
            true_path.write_text(sanitized_content, encoding="utf-8")
            report.append(f"Deploy Successful: {clean_filepath}")

        return "\n".join(report)

    @staticmethod
    def run_tests() -> str:
        """Execute the configured test command through a shell so project-local chaining works."""
        try:
            test_cwd = TARGET_PROJECT_PATH if os.path.isdir(
                TARGET_PROJECT_PATH) else ROOT_DIR
            res = subprocess.run(
                ["bash", "-lc", TEST_COMMAND],
                capture_output=True,
                text=True,
                cwd=test_cwd,
                check=False,
            )
            if res.returncode == 0:
                return "PASS"
            return "\n".join(part for part in [res.stdout.strip(), res.stderr.strip()] if part)
        except Exception as e:
            return f"System Execution Fault: {str(e)}"

# =====================================================================
# 4. Asynchronous Framework Main Runtime
# =====================================================================


async def main():
    print("🔍 Inspecting active architectural blueprints...")
    try:
        pending_work = MarkdownPlanParser.get_pending_slices(PLAN_FILE_PATH)
    except Exception as e:
        print(f"Aborting runtime initialization: {e}")
        return

    if not pending_work:
        print("🎉 All targets matched. Workspace status up to date!")
        return

    print(
        f"🚀 Loaded {len(pending_work)} outstanding architectural tasks. Spawning local LLM engines...")
    culprit_slices: List[Dict[str, Any]] = []

    if not llm_backend_available(LLM_BASE_URL):
        print(
            f"⚠️ No LLM backend detected at {LLM_BASE_URL}. "
            "Start Ollama or set LLM_BASE_URL before running the live orchestrator."
        )
        return

    # 1. Instantiate the OpenAI-compatible clients directly for Ollama
    local_coder_client = OpenAIChatClient(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL_DEFAULT,
    )

    local_qa_client = OpenAIChatClient(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL_DEFAULT,
    )

    # 2. Instantiate specialized personas using ChatAgent
    coder_agent = Agent(
        client=local_coder_client,
        name="SliceDeveloper",
        instructions=(
            "You are an expert backend engineer implementing isolated feature folder components "
            "using Vertical Slice Architecture guidelines. Your response must contain only file blocks. "
            "No explanations, no markdown prose, and no code fences outside the file blocks. "
            "Use this exact format for every file:\n"
            "--- FILE: relative/path/to/target/file.ts ---\n"
            "[Your complete file code here]\n"
            "--- END FILE ---\n"
            "If you create multiple files, emit multiple blocks in sequence. "
            "Do not omit the file boundary markers. Generate real code based on the user's slice requirement."
        )
    )

    qa_agent = Agent(
        client=local_qa_client,
        name="VerificationQA",
        instructions=(
            "You verify code stability. Inspect the written structures and compilation terminal logs. "
            "If failures are apparent, issue code corrections back to the developer explicitly."
        )
    )

    formatter_agent = Agent(
        client=local_coder_client,
        name="FileBlockFormatter",
        instructions=(
            "You normalize raw coding output into strict deployable file blocks only. "
            "Return only this format and nothing else:\n"
            "--- FILE: relative/path/from/repo/root.ext ---\n"
            "<full file contents>\n"
            "--- END FILE ---\n"
            "No prose, no analysis, no markdown headings."
        ),
    )

    # Process outstanding array tasks sequentially
    for item in pending_work:
        print(f"\n==================================================================")
        print(
            f"⚡ MAF STARTING SUPERSTEP: Slice {item['number']} — {item['name']}")
        print(f"==================================================================")

        # Enforce deterministic agent message passing route using SequentialBuilder
        slice_workflow = (
            SequentialBuilder(
                participants=[coder_agent, qa_agent]
            ).build()
        )

        initial_prompt = (
            f"Implement the following slice exactly.\n\n"
            f"{item['markdown_content']}\n\n"
            "Return only valid file blocks using this exact schema and nothing else:\n\n"
            "--- FILE: relative/path/from/repo/root.ext ---\n"
            "<full file contents here, without markdown fences>\n"
            "--- END FILE ---\n\n"
            "Rules:\n"
            "1. Output only file blocks. No commentary, no explanation, no Markdown headings, no prose.\n"
            "2. Each file must use the exact boundary markers shown above.\n"
            "3. Do not wrap the file contents in triple backticks.\n"
            "4. If there are multiple files, emit multiple blocks in sequence.\n"
            "5. Use real code matching the slice requirements and project structure."
        )

        # 1. Trigger the collaborative Multi-Agent execution graph
        print("[MAF] Routing task to development core...")
        try:
            workflow_session = await slice_workflow.run(initial_prompt)
        except Exception as exc:
            print(
                f"[MAF] Agent workflow failed for slice {item['number']}: {exc}")
            continue

        final_message = ""
        candidate_payloads: List[str] = []
        messages_list = []
        if hasattr(workflow_session, 'get_outputs'):
            outputs = workflow_session.get_outputs()
            if outputs:
                messages_list = outputs
                candidate_payloads.extend(
                    extract_text_payload(output_item) for output_item in outputs
                )
        if not messages_list and hasattr(workflow_session, 'state') and 'messages' in workflow_session.state:
            messages_list = workflow_session.state['messages']
        elif not messages_list and hasattr(workflow_session, 'messages'):
            messages_list = workflow_session.messages
        elif not messages_list:
            messages_list = getattr(
                workflow_session, 'context', {}).get('messages', [])

        if messages_list:
            candidate_payloads.extend(
                extract_text_payload(msg_item) for msg_item in messages_list
            )

        print("\n--- [CONVERSATION TRAIL LOGS] ---")
        for msg in messages_list:
            content = extract_text_payload(msg)
            if not content:
                continue
            author = msg.get('author_name', 'Agent') if isinstance(
                msg, dict) else getattr(msg, 'author_name', 'Agent')
            preview = content[:200].replace("\n", " ") if len(
                content) > 200 else content.replace("\n", " ")
            print(f"🔹 [{author}]: {preview}...")
            candidate_payloads.append(content)
        print("---------------------------------\n")

        fallback_payload = extract_text_payload(workflow_session)
        if fallback_payload:
            candidate_payloads.append(fallback_payload)

        final_message = choose_best_file_block_payload(candidate_payloads)

        if not final_message:
            print(
                "[MAF] Primary payload had no deployable file blocks. Invoking formatter recovery agent...")
            recovery_prompt = (
                "Normalize the following raw output into valid file blocks only. "
                "If code is incomplete, synthesize complete files from the slice requirements.\n\n"
                f"Slice requirements:\n{item['markdown_content']}\n\n"
                "Raw outputs:\n"
                + "\n\n".join(candidate_payloads[-8:])
            )
            try:
                formatter_session = await formatter_agent.run(recovery_prompt)
                final_message = extract_text_payload(formatter_session)
            except Exception as exc:
                print(f"[MAF] Formatter recovery failed: {exc}")
                final_message = ""

        # 3. Write files emitted by the agents to your real project disk
        print("[MAF] Extracting code payloads and writing to filesystem...")
        disk_report = LocalWorkspaceTools.write_files_from_markdown(
            final_message)
        print(disk_report)

        if "Warning: No clean file structural syntax blocks matched or generated." in disk_report:
            print(
                "[MAF] First write pass failed. Requesting a second-pass formatter correction...")
            retry_prompt = (
                "Rewrite this into valid file blocks only using the exact required format.\n\n"
                f"Slice requirements:\n{item['markdown_content']}\n\n"
                f"Current output:\n{final_message}"
            )
            try:
                formatter_retry_session = await formatter_agent.run(retry_prompt)
                retry_message = extract_text_payload(formatter_retry_session)
                disk_report = LocalWorkspaceTools.write_files_from_markdown(
                    retry_message)
                print(disk_report)
            except Exception as exc:
                print(f"[MAF] Formatter second pass failed: {exc}")

        if "Warning: No clean file structural syntax blocks matched or generated." in disk_report:
            print(
                f"[MAF] No deployable files produced for slice {item['number']} after self-healing. Skipping validation for this slice.")
            continue

        # 4. Verification Checkpoint loop
        print(f"[MAF] Running test validation suites via: '{TEST_COMMAND}'...")
        test_status = LocalWorkspaceTools.run_tests()

        if test_status == "PASS":
            print(
                f"✅ Slice {item['number']} Verified Green! Bundling local workspace to Git history...")
            try:
                MarkdownPlanParser.mark_slice_complete(
                    PLAN_FILE_PATH, item['number'])
            except Exception:
                pass
            repo_base = os.path.join(TARGET_PROJECT_PATH, "..")
            commit_all_changes(
                repo_base, f"maf-agent: slice {item['number']} compiled ({item['name']})")
        else:
            print(
                f"❌ Slice {item['number']} build failed integration testing checks. Initiating self-healing protocol...")

            healed = False
            latest_failure = test_status

            for attempt in range(1, MAX_HEALING_ITERATIONS + 1):
                print(
                    f"[MAF] Self-healing attempt {attempt}/{MAX_HEALING_ITERATIONS} for Slice {item['number']}...")
                healing_prompt = (
                    "You are fixing the same slice after failing tests. "
                    "Return only strict file blocks and directly address this failure output.\n\n"
                    f"Slice number: {item['number']}\n"
                    f"Slice name: {item['name']}\n\n"
                    "Latest failing test output:\n"
                    f"{latest_failure}\n\n"
                    "Required output format:\n"
                    "--- FILE: relative/path/from/repo/root.ext ---\n"
                    "<full file contents>\n"
                    "--- END FILE ---"
                )

                try:
                    healing_session = await coder_agent.run(healing_prompt)
                except Exception as exc:
                    latest_failure = f"Developer healing agent failed to run: {exc}"
                    print(f"[MAF] {latest_failure}")
                    continue

                healing_text_payload = extract_text_payload(healing_session)
                healing_report = LocalWorkspaceTools.write_files_from_markdown(
                    healing_text_payload)
                print(healing_report)

                if "Warning: No clean file structural syntax blocks matched or generated." in healing_report:
                    formatter_prompt = (
                        "Normalize this raw developer output into valid file blocks only.\n\n"
                        f"Slice requirements:\n{item['markdown_content']}\n\n"
                        f"Raw developer output:\n{healing_text_payload}"
                    )
                    try:
                        formatter_session = await formatter_agent.run(formatter_prompt)
                        formatted_payload = extract_text_payload(
                            formatter_session)
                        healing_report = LocalWorkspaceTools.write_files_from_markdown(
                            formatted_payload)
                        print(healing_report)
                    except Exception as exc:
                        print(
                            f"[MAF] Formatter during self-healing failed: {exc}")

                if "Warning: No clean file structural syntax blocks matched or generated." in healing_report:
                    latest_failure = "Self-healing produced no deployable file blocks."
                    continue

                final_check = LocalWorkspaceTools.run_tests()
                if final_check == "PASS":
                    healed = True
                    break

                latest_failure = final_check

            if healed:
                print("✅ Self-healing loop successful! Slice verified.")
                try:
                    MarkdownPlanParser.mark_slice_complete(
                        PLAN_FILE_PATH, item['number'])
                except Exception:
                    pass
                repo_base = os.path.join(TARGET_PROJECT_PATH, "..")
                commit_all_changes(
                    repo_base, f"maf-agent: slice {item['number']} self-healed and compiled")
            else:
                culprit = {
                    "number": item["number"],
                    "name": item["name"],
                    "failure": latest_failure,
                }
                culprit_slices.append(culprit)
                print(
                    f"🚨 Slice {item['number']} exceeded self-healing limit ({MAX_HEALING_ITERATIONS}). "
                    "Marking as culprit and continuing best-effort with remaining slices.")

    if culprit_slices:
        print("\n[MAF] Culprit slices requiring manual investigation:")
        for culprit in culprit_slices:
            snippet = str(culprit["failure"]).strip().replace("\n", " ")
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."
            print(
                f" - Slice {culprit['number']} — {culprit['name']}: {snippet}")


if __name__ == "__main__":
    asyncio.run(main())
