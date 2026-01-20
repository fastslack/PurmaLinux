"""
PurmaLinux - Multi-Agent System
Specialized AI agents that collaborate to solve complex tasks

Agents:
- Orchestrator: Coordinates tasks between agents
- Researcher: Searches files, web, documentation
- Analyzer: Analyzes data, code, patterns
- Executor: Runs commands, modifies files
- Reviewer: Validates results, suggests improvements
- Specialist: Domain-specific experts (code, security, etc.)
"""

import os
import json
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import subprocess
import httpx
import re

# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class AgentRole(Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    CODER = "coder"
    SECURITY = "security"
    DEVOPS = "devops"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATED = "delegated"

@dataclass
class AgentMessage:
    """Message between agents"""
    from_agent: str
    to_agent: str
    message_type: str  # "task", "result", "query", "feedback"
    content: Dict
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = None

@dataclass
class Task:
    """A task to be executed by an agent"""
    id: str
    description: str
    assigned_to: str = None
    created_by: str = "user"
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1  # 1-5, 5 highest
    context: Dict = field(default_factory=dict)
    subtasks: List['Task'] = field(default_factory=list)
    result: Any = None
    error: str = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None

@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    name: str
    description: str
    input_schema: Dict = None
    output_schema: Dict = None

@dataclass
class AgentState:
    """Current state of an agent"""
    is_busy: bool = False
    current_task: Optional[Task] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_activity: datetime = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Base Agent
# ═══════════════════════════════════════════════════════════════════════════════

class BaseAgent(ABC):
    """Abstract base class for all agents"""

    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.state = AgentState()
        self.capabilities: List[AgentCapability] = []
        self.message_handlers: Dict[str, Callable] = {}
        self.ollama_url = "http://localhost:11434"
        self.model = "llama3.2"

    @abstractmethod
    async def execute_task(self, task: Task) -> Any:
        """Execute a task - must be implemented by subclasses"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """Return agent capabilities"""
        pass

    async def think(self, prompt: str, context: Dict = None) -> str:
        """Use LLM to think/reason"""
        full_prompt = f"""You are {self.name}, a {self.role.value} agent in PurmaLinux.
Your capabilities: {', '.join(c.name for c in self.capabilities)}

{f'Context: {json.dumps(context)}' if context else ''}

Task: {prompt}

Respond with your analysis and recommended action."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": full_prompt, "stream": False},
                    timeout=60
                )

                if response.status_code == 200:
                    return response.json().get("response", "")
        except Exception as e:
            return f"Thinking error: {e}"

        return ""

    async def send_message(self, to_agent: str, message_type: str, content: Dict) -> AgentMessage:
        """Send message to another agent"""
        return AgentMessage(
            from_agent=self.name,
            to_agent=to_agent,
            message_type=message_type,
            content=content
        )

    def update_state(self, **kwargs):
        """Update agent state"""
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.last_activity = datetime.now()


# ═══════════════════════════════════════════════════════════════════════════════
#  Specialized Agents
# ═══════════════════════════════════════════════════════════════════════════════

class ResearcherAgent(BaseAgent):
    """Agent specialized in finding information"""

    def __init__(self):
        super().__init__("Researcher", AgentRole.RESEARCHER)
        self.capabilities = self.get_capabilities()

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="search_files",
                description="Search for files by name or content"
            ),
            AgentCapability(
                name="search_code",
                description="Search code for patterns, functions, classes"
            ),
            AgentCapability(
                name="read_file",
                description="Read and extract content from files"
            ),
            AgentCapability(
                name="search_docs",
                description="Search documentation and manuals"
            ),
            AgentCapability(
                name="web_search",
                description="Search the web for information"
            )
        ]

    async def execute_task(self, task: Task) -> Any:
        self.update_state(is_busy=True, current_task=task)

        try:
            task_type = task.context.get("type", "general")

            if task_type == "search_files":
                return await self._search_files(task)
            elif task_type == "search_code":
                return await self._search_code(task)
            elif task_type == "read_file":
                return await self._read_file(task)
            else:
                # Use LLM to determine action
                thought = await self.think(task.description, task.context)
                return {"thought": thought, "action": "analyzed"}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _search_files(self, task: Task) -> Dict:
        """Search for files"""
        query = task.context.get("query", "")
        path = task.context.get("path", os.path.expanduser("~"))

        try:
            result = subprocess.run(
                ["find", path, "-name", f"*{query}*", "-type", "f"],
                capture_output=True, text=True, timeout=30
            )

            files = result.stdout.strip().split("\n")[:20]  # Limit results
            return {"files": [f for f in files if f], "count": len(files)}
        except Exception as e:
            return {"error": str(e)}

    async def _search_code(self, task: Task) -> Dict:
        """Search code with ripgrep"""
        pattern = task.context.get("pattern", "")
        path = task.context.get("path", ".")
        file_type = task.context.get("file_type")

        cmd = ["rg", "--json", pattern, path]
        if file_type:
            cmd.extend(["-t", file_type])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            matches = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "match":
                            matches.append({
                                "file": data["data"]["path"]["text"],
                                "line": data["data"]["line_number"],
                                "text": data["data"]["lines"]["text"].strip()
                            })
                    except:
                        pass

            return {"matches": matches[:20], "count": len(matches)}
        except Exception as e:
            return {"error": str(e)}

    async def _read_file(self, task: Task) -> Dict:
        """Read file content"""
        filepath = task.context.get("path", "")

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return {
                "path": filepath,
                "content": content[:10000],  # Limit size
                "size": len(content),
                "truncated": len(content) > 10000
            }
        except Exception as e:
            return {"error": str(e)}


class AnalyzerAgent(BaseAgent):
    """Agent specialized in analysis"""

    def __init__(self):
        super().__init__("Analyzer", AgentRole.ANALYZER)
        self.capabilities = self.get_capabilities()

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="analyze_code",
                description="Analyze code structure, complexity, issues"
            ),
            AgentCapability(
                name="analyze_data",
                description="Analyze data patterns and statistics"
            ),
            AgentCapability(
                name="analyze_logs",
                description="Analyze log files for errors and patterns"
            ),
            AgentCapability(
                name="compare",
                description="Compare files, versions, or data"
            ),
            AgentCapability(
                name="summarize",
                description="Summarize content or findings"
            )
        ]

    async def execute_task(self, task: Task) -> Any:
        self.update_state(is_busy=True, current_task=task)

        try:
            task_type = task.context.get("type", "general")

            if task_type == "analyze_code":
                return await self._analyze_code(task)
            elif task_type == "analyze_logs":
                return await self._analyze_logs(task)
            elif task_type == "summarize":
                return await self._summarize(task)
            else:
                # Use LLM for general analysis
                thought = await self.think(
                    f"Analyze the following:\n{task.description}",
                    task.context
                )
                return {"analysis": thought}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _analyze_code(self, task: Task) -> Dict:
        """Analyze code file"""
        filepath = task.context.get("path", "")

        try:
            with open(filepath, "r") as f:
                code = f.read()

            # Basic metrics
            lines = code.split("\n")
            total_lines = len(lines)
            code_lines = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
            comment_lines = len([l for l in lines if l.strip().startswith("#")])

            # Use LLM for deeper analysis
            analysis = await self.think(
                f"Analyze this code for quality, potential issues, and improvements:\n\n{code[:3000]}",
                {"file": filepath, "language": os.path.splitext(filepath)[1]}
            )

            return {
                "file": filepath,
                "metrics": {
                    "total_lines": total_lines,
                    "code_lines": code_lines,
                    "comment_lines": comment_lines,
                    "comment_ratio": round(comment_lines / max(total_lines, 1), 2)
                },
                "analysis": analysis
            }
        except Exception as e:
            return {"error": str(e)}

    async def _analyze_logs(self, task: Task) -> Dict:
        """Analyze log file"""
        filepath = task.context.get("path", "")
        pattern = task.context.get("pattern", r"error|warning|fail|exception")

        try:
            with open(filepath, "r", errors="ignore") as f:
                lines = f.readlines()[-1000:]  # Last 1000 lines

            issues = []
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line": i + 1,
                        "content": line.strip()[:200]
                    })

            return {
                "file": filepath,
                "total_lines": len(lines),
                "issues_found": len(issues),
                "issues": issues[:50]  # Limit
            }
        except Exception as e:
            return {"error": str(e)}

    async def _summarize(self, task: Task) -> Dict:
        """Summarize content"""
        content = task.context.get("content", task.description)

        summary = await self.think(
            f"Summarize the following concisely:\n\n{content[:5000]}"
        )

        return {"summary": summary}


class ExecutorAgent(BaseAgent):
    """Agent specialized in executing actions"""

    def __init__(self):
        super().__init__("Executor", AgentRole.EXECUTOR)
        self.capabilities = self.get_capabilities()
        self.safe_mode = True  # Require confirmation for dangerous ops

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="run_command",
                description="Execute shell commands"
            ),
            AgentCapability(
                name="write_file",
                description="Write content to files"
            ),
            AgentCapability(
                name="edit_file",
                description="Edit existing files"
            ),
            AgentCapability(
                name="install_package",
                description="Install system packages"
            ),
            AgentCapability(
                name="manage_service",
                description="Start/stop system services"
            )
        ]

    async def execute_task(self, task: Task) -> Any:
        self.update_state(is_busy=True, current_task=task)

        try:
            task_type = task.context.get("type", "")

            if task_type == "run_command":
                return await self._run_command(task)
            elif task_type == "write_file":
                return await self._write_file(task)
            elif task_type == "edit_file":
                return await self._edit_file(task)
            else:
                return {"error": "Unknown task type", "supported": [c.name for c in self.capabilities]}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _run_command(self, task: Task) -> Dict:
        """Run shell command"""
        command = task.context.get("command", "")

        if not command:
            return {"error": "No command provided"}

        # Safety check
        dangerous_patterns = ["rm -rf", "dd if=", "> /dev/", "mkfs", ":(){", "chmod -R 777"]
        for pattern in dangerous_patterns:
            if pattern in command:
                if self.safe_mode:
                    return {
                        "error": "Dangerous command blocked",
                        "command": command,
                        "reason": f"Contains dangerous pattern: {pattern}"
                    }

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=task.context.get("timeout", 60)
            )

            return {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:1000],
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "command": command}
        except Exception as e:
            return {"error": str(e), "command": command}

    async def _write_file(self, task: Task) -> Dict:
        """Write content to file"""
        filepath = task.context.get("path", "")
        content = task.context.get("content", "")
        mode = task.context.get("mode", "w")

        if not filepath:
            return {"error": "No file path provided"}

        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            with open(filepath, mode) as f:
                f.write(content)

            return {
                "path": filepath,
                "size": len(content),
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}

    async def _edit_file(self, task: Task) -> Dict:
        """Edit file (find and replace)"""
        filepath = task.context.get("path", "")
        find = task.context.get("find", "")
        replace = task.context.get("replace", "")

        if not filepath or not find:
            return {"error": "Missing path or find pattern"}

        try:
            with open(filepath, "r") as f:
                content = f.read()

            if find not in content:
                return {"error": "Pattern not found", "path": filepath, "pattern": find}

            new_content = content.replace(find, replace)

            with open(filepath, "w") as f:
                f.write(new_content)

            return {
                "path": filepath,
                "changes": content.count(find),
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "path": filepath}


class CoderAgent(BaseAgent):
    """Agent specialized in code generation and modification"""

    def __init__(self):
        super().__init__("Coder", AgentRole.CODER)
        self.capabilities = self.get_capabilities()

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="generate_code",
                description="Generate code from description"
            ),
            AgentCapability(
                name="fix_code",
                description="Fix bugs and errors in code"
            ),
            AgentCapability(
                name="refactor",
                description="Refactor code for better quality"
            ),
            AgentCapability(
                name="explain_code",
                description="Explain what code does"
            ),
            AgentCapability(
                name="add_tests",
                description="Generate tests for code"
            )
        ]

    async def execute_task(self, task: Task) -> Any:
        self.update_state(is_busy=True, current_task=task)

        try:
            task_type = task.context.get("type", "generate")

            if task_type == "generate_code":
                return await self._generate_code(task)
            elif task_type == "fix_code":
                return await self._fix_code(task)
            elif task_type == "explain_code":
                return await self._explain_code(task)
            else:
                thought = await self.think(task.description, task.context)
                return {"response": thought}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _generate_code(self, task: Task) -> Dict:
        """Generate code from description"""
        description = task.description
        language = task.context.get("language", "python")

        prompt = f"""Generate {language} code for the following:

{description}

Requirements:
- Clean, readable code
- Include comments
- Follow best practices
- Handle edge cases

Respond with ONLY the code, no explanations."""

        code = await self.think(prompt)

        # Extract code block if present
        if "```" in code:
            matches = re.findall(r"```(?:\w+)?\n(.*?)```", code, re.DOTALL)
            if matches:
                code = matches[0]

        return {
            "language": language,
            "code": code.strip(),
            "description": description
        }

    async def _fix_code(self, task: Task) -> Dict:
        """Fix code bugs"""
        code = task.context.get("code", "")
        error = task.context.get("error", "")

        prompt = f"""Fix the following code:

```
{code}
```

Error: {error}

Provide the corrected code."""

        fixed = await self.think(prompt)

        return {
            "original": code,
            "fixed": fixed,
            "error": error
        }

    async def _explain_code(self, task: Task) -> Dict:
        """Explain code"""
        code = task.context.get("code", task.description)

        prompt = f"""Explain what this code does in simple terms:

```
{code}
```

Include:
- Overall purpose
- Key functions/components
- How it works step by step"""

        explanation = await self.think(prompt)

        return {"code": code, "explanation": explanation}


class ReviewerAgent(BaseAgent):
    """Agent specialized in reviewing and validating"""

    def __init__(self):
        super().__init__("Reviewer", AgentRole.REVIEWER)
        self.capabilities = self.get_capabilities()

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="review_code",
                description="Review code for quality and issues"
            ),
            AgentCapability(
                name="review_plan",
                description="Review and validate a plan"
            ),
            AgentCapability(
                name="validate_result",
                description="Validate task results"
            ),
            AgentCapability(
                name="security_review",
                description="Review for security issues"
            )
        ]

    async def execute_task(self, task: Task) -> Any:
        self.update_state(is_busy=True, current_task=task)

        try:
            task_type = task.context.get("type", "review")

            if task_type == "review_code":
                return await self._review_code(task)
            elif task_type == "validate_result":
                return await self._validate_result(task)
            else:
                review = await self.think(
                    f"Review and provide feedback on:\n{task.description}",
                    task.context
                )
                return {"review": review}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _review_code(self, task: Task) -> Dict:
        """Review code"""
        code = task.context.get("code", "")

        prompt = f"""Review this code critically:

```
{code}
```

Evaluate:
1. Code quality (1-10)
2. Readability (1-10)
3. Potential bugs
4. Security issues
5. Performance concerns
6. Suggestions for improvement

Be specific and thorough."""

        review = await self.think(prompt)

        return {"code": code, "review": review}

    async def _validate_result(self, task: Task) -> Dict:
        """Validate a task result"""
        result = task.context.get("result", {})
        expected = task.context.get("expected", {})

        prompt = f"""Validate this result:

Result: {json.dumps(result, indent=2)}

Expected: {json.dumps(expected, indent=2)}

Determine if the result meets expectations and explain any discrepancies."""

        validation = await self.think(prompt)

        return {
            "result": result,
            "expected": expected,
            "validation": validation,
            "passed": "error" not in str(result).lower()
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Orchestrator Agent
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorAgent(BaseAgent):
    """Master agent that coordinates other agents"""

    def __init__(self, agents: Dict[str, BaseAgent] = None):
        super().__init__("Orchestrator", AgentRole.ORCHESTRATOR)
        self.agents = agents or {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        self.message_log: List[AgentMessage] = []

    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="plan_task",
                description="Break down complex tasks into subtasks"
            ),
            AgentCapability(
                name="delegate_task",
                description="Assign tasks to appropriate agents"
            ),
            AgentCapability(
                name="coordinate",
                description="Coordinate multi-agent workflows"
            ),
            AgentCapability(
                name="synthesize",
                description="Combine results from multiple agents"
            )
        ]

    def register_agent(self, agent: BaseAgent):
        """Register an agent"""
        self.agents[agent.name] = agent

    def get_best_agent(self, task: Task) -> Optional[BaseAgent]:
        """Find best agent for a task"""
        task_type = task.context.get("type", "").lower()
        description = task.description.lower()

        # Match by task type or description keywords
        agent_keywords = {
            "Researcher": ["search", "find", "look for", "where", "read"],
            "Analyzer": ["analyze", "review", "check", "summarize", "compare"],
            "Executor": ["run", "execute", "install", "write", "create file"],
            "Coder": ["code", "function", "class", "implement", "fix bug"],
            "Reviewer": ["review", "validate", "verify", "security"]
        }

        for agent_name, keywords in agent_keywords.items():
            if agent_name in self.agents:
                for keyword in keywords:
                    if keyword in task_type or keyword in description:
                        return self.agents[agent_name]

        # Default to first available
        return next(iter(self.agents.values()), None)

    async def plan_task(self, description: str, context: Dict = None) -> List[Task]:
        """Break down a complex task into subtasks"""
        prompt = f"""Break down this task into steps:

Task: {description}
Context: {json.dumps(context or {})}

For each step, specify:
1. Description
2. Type (search, analyze, execute, code, review)
3. Dependencies (which steps must complete first)

Respond as JSON array of steps."""

        plan_response = await self.think(prompt)

        # Parse response (simplified)
        subtasks = []
        task_id_base = f"task_{datetime.now().strftime('%H%M%S')}"

        # Try to parse as JSON
        try:
            if "[" in plan_response:
                json_str = plan_response[plan_response.find("["):plan_response.rfind("]")+1]
                steps = json.loads(json_str)

                for i, step in enumerate(steps):
                    subtasks.append(Task(
                        id=f"{task_id_base}_{i}",
                        description=step.get("description", str(step)),
                        context={"type": step.get("type", "general")},
                        priority=5 - i  # Higher priority for earlier steps
                    ))
        except:
            # Fallback: single task
            subtasks.append(Task(
                id=f"{task_id_base}_0",
                description=description,
                context=context or {}
            ))

        return subtasks

    async def execute_task(self, task: Task) -> Any:
        """Execute a task (orchestrator delegates)"""
        self.update_state(is_busy=True, current_task=task)

        try:
            # Plan subtasks if complex
            if len(task.description) > 100 or task.context.get("complex"):
                subtasks = await self.plan_task(task.description, task.context)
            else:
                subtasks = [task]

            results = []

            for subtask in subtasks:
                # Find best agent
                agent = self.get_best_agent(subtask)

                if agent:
                    subtask.assigned_to = agent.name
                    subtask.status = TaskStatus.IN_PROGRESS

                    # Execute
                    result = await agent.execute_task(subtask)
                    subtask.result = result
                    subtask.status = TaskStatus.COMPLETED
                    subtask.completed_at = datetime.now()

                    results.append({
                        "task": subtask.description,
                        "agent": agent.name,
                        "result": result
                    })

                    # Log message
                    self.message_log.append(AgentMessage(
                        from_agent=agent.name,
                        to_agent=self.name,
                        message_type="result",
                        content={"task_id": subtask.id, "result": result}
                    ))
                else:
                    subtask.status = TaskStatus.FAILED
                    subtask.error = "No suitable agent found"

            # Synthesize results
            if len(results) > 1:
                synthesis = await self._synthesize_results(results)
                return {"subtasks": results, "synthesis": synthesis}

            return results[0]["result"] if results else {"error": "No results"}

        finally:
            self.update_state(is_busy=False, current_task=None)
            self.state.tasks_completed += 1

    async def _synthesize_results(self, results: List[Dict]) -> str:
        """Combine results from multiple agents"""
        prompt = f"""Synthesize these results into a coherent response:

{json.dumps(results, indent=2)}

Provide a clear summary of findings and conclusions."""

        return await self.think(prompt)

    def get_status(self) -> Dict:
        """Get orchestrator status"""
        return {
            "agents": {
                name: {
                    "role": agent.role.value,
                    "busy": agent.state.is_busy,
                    "tasks_completed": agent.state.tasks_completed,
                    "capabilities": [c.name for c in agent.capabilities]
                }
                for name, agent in self.agents.items()
            },
            "task_queue": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "messages": len(self.message_log)
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Multi-Agent Engine
# ═══════════════════════════════════════════════════════════════════════════════

class MultiAgentEngine:
    """Main engine for multi-agent system"""

    def __init__(self):
        # Create specialized agents
        self.researcher = ResearcherAgent()
        self.analyzer = AnalyzerAgent()
        self.executor = ExecutorAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()

        # Create orchestrator with all agents
        self.orchestrator = OrchestratorAgent({
            "Researcher": self.researcher,
            "Analyzer": self.analyzer,
            "Executor": self.executor,
            "Coder": self.coder,
            "Reviewer": self.reviewer
        })

    async def run(self, description: str, context: Dict = None) -> Dict:
        """Run a task through the multi-agent system"""
        task = Task(
            id=f"main_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description=description,
            context=context or {},
            created_by="user"
        )

        result = await self.orchestrator.execute_task(task)

        return {
            "task": description,
            "result": result,
            "status": "completed"
        }

    async def ask_agent(self, agent_name: str, description: str, context: Dict = None) -> Dict:
        """Ask a specific agent directly"""
        agents = {
            "researcher": self.researcher,
            "analyzer": self.analyzer,
            "executor": self.executor,
            "coder": self.coder,
            "reviewer": self.reviewer
        }

        agent = agents.get(agent_name.lower())
        if not agent:
            return {"error": f"Unknown agent: {agent_name}", "available": list(agents.keys())}

        task = Task(
            id=f"direct_{datetime.now().strftime('%H%M%S')}",
            description=description,
            context=context or {},
            assigned_to=agent.name
        )

        result = await agent.execute_task(task)

        return {
            "agent": agent.name,
            "task": description,
            "result": result
        }

    def get_status(self) -> Dict:
        """Get system status"""
        return self.orchestrator.get_status()

    def get_agents(self) -> List[Dict]:
        """Get list of available agents"""
        agents = []
        for name, agent in self.orchestrator.agents.items():
            agents.append({
                "name": name,
                "role": agent.role.value,
                "capabilities": [
                    {"name": c.name, "description": c.description}
                    for c in agent.capabilities
                ]
            })
        return agents


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════════════════════

_agent_engine = None

def get_agent_engine() -> MultiAgentEngine:
    global _agent_engine
    if _agent_engine is None:
        _agent_engine = MultiAgentEngine()
    return _agent_engine
