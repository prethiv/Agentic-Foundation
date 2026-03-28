import os
import subprocess
import operator
import boto3
from typing import Annotated, TypedDict, Union, Literal
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver


# --- 1. State Definition ---
class AgentState(TypedDict):
    repo_url: str
    local_path: str
    project_type: str  # android, ios, kmp, java, node, frontend
    coverage: float
    iteration_count: Annotated[int, operator.add]
    error_log: str


# --- 2. Initialize AWS Clients ---
# Using Claude 3.5 Sonnet for its superior coding capabilities
llm = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")
ses_client = boto3.client('ses', region_name='us-east-1')


# --- 3. Node Functions ---

def clone_and_detect(state: AgentState):
    repo_name = state['repo_url'].split('/')[-1].replace(".git", "")
    path = f"/tmp/{repo_name}"

    # Clone Repo
    if not os.path.exists(path):
        subprocess.run(["git", "clone", state['repo_url'], path])

    # Simple Heuristic Detection
    p_type = "unknown"
    if os.path.exists(f"{path}/package.json"):
        p_type = "node_or_frontend"
    elif os.path.exists(f"{path}/build.gradle") or os.path.exists(f"{path}/build.gradle.kts"):
        # Check for Android vs KMP vs Java Service
        with open(f"{path}/build.gradle", "r") if os.path.exists(f"{path}/build.gradle") else open(
                f"{path}/build.gradle.kts", "r") as f:
            content = f.read()
            if "com.android.application" in content:
                p_type = "android"
            elif "multiplatform" in content:
                p_type = "kmp"
            else:
                p_type = "java_service"

    return {"local_path": path, "project_type": p_type, "iteration_count": 0}


def run_test_and_coverage(state: AgentState):
    path = state['local_path']
    p_type = state['project_type']
    coverage_val = 0.0

    try:
        if "node" in p_type:
            # Example for Node/React
            subprocess.run(["npm", "install"], cwd=path)
            result = subprocess.run(["npm", "test", "--", "--coverage", "--json"], cwd=path, capture_output=True)
            # In a real scenario, you'd parse the coverage.json here
            coverage_val = 65.0  # Mocking initial failure
        elif p_type == "java_service":
            subprocess.run(["./gradlew", "test", "jacocoTestReport"], cwd=path)
            coverage_val = 70.0  # Mocking initial failure

    except Exception as e:
        return {"error_log": str(e)}

    return {"coverage": coverage_val}


def write_ai_tests(state: AgentState):
    # Construct prompt for the LLM to write tests
    prompt = f"The {state['project_type']} project at {state['repo_url']} has {state['coverage']}% coverage. " \
             f"Write missing unit tests with assertions for the main logic to reach 90%."

    response = llm.invoke(prompt)
    # logic to save response.content to a new test file in state['local_path']
    print(f"--- AI Writing Tests (Iteration {state['iteration_count'] + 1}) ---")

    return {"iteration_count": 1}  # Increments global state


def send_notifications(state: AgentState):
    if state['coverage'] >= 90:
        msg = f"Success! Coverage is {state['coverage']}%."
        subject = "✅ Unit Test Coverage Passed"
    else:
        msg = f"Agent stopped after 5 attempts. Current coverage: {state['coverage']}%."
        subject = "⚠️ Manual Action Required"

    ses_client.send_email(
        Source='ai-agent@yourdomain.com',
        Destination={'ToAddresses': ['prethiv191@gmail.com']},
        Message={'Subject': {'Data': subject}, 'Body': {'Text': {'Data': msg}}}
    )
    return state


# --- 4. Routing Logic ---

def router(state: AgentState) -> Literal["write_more", "notify", "end"]:
    if state['coverage'] >= 90:
        return "notify"
    if state['iteration_count'] >= 5:
        return "notify"
    if state['coverage'] < 80:
        return "write_more"
    return "end"


# --- 5. Build the Graph ---

workflow = StateGraph(AgentState)

workflow.add_node("setup", clone_and_detect)
workflow.add_node("test", run_test_and_coverage)
workflow.add_node("write_more", write_ai_tests)
workflow.add_node("notify", send_notifications)

workflow.add_edge(START, "setup")
workflow.add_edge("setup", "test")

workflow.add_conditional_edges(
    "test",
    router,
    {
        "write_more": "write_more",
        "notify": "notify",
        "end": END
    }
)

workflow.add_edge("write_more", "test")
workflow.add_edge("notify", END)

# Compile with memory so it saves state (Checkpointer)
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# --- 6. Execution ---
config = {"configurable": {"thread_id": "repo-check-001"}}
initial_input = {"repo_url": "https://github.com/your-username/sample-java-service.git"}

for event in app.stream(initial_input, config):
    print(event)
