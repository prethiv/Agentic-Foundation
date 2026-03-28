from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 'add_messages' tells LangGraph to append new messages instead of overwriting
    messages: Annotated[list, add_messages]
    at_risk: bool  # Custom field for your business logic

from langchain_aws import ChatBedrock

# Initialize the 'Brain' using Claude 3.5 on AWS Bedrock
model = ChatBedrock(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0")

def call_model(state: AgentState):
    response = model.invoke(state["messages"])
    return {"messages": [response]}

def check_safety(state: AgentState):
    # Example logic: if the user mentions 'crypto loss', flag it
    last_msg = state["messages"][-1].content
    if "loss" in last_msg.lower():
        return {"at_risk": True}
    return {"at_risk": False}


def should_continue(state: AgentState):
    # If the LLM called a tool, go to the 'tools' node
    if state["messages"][-1].tool_calls:
        return "tools"
    # Otherwise, finish
    return "end"


from langgraph.graph import StateGraph, START, END

workflow = StateGraph(AgentState)

# Add our nodes
workflow.add_node("agent", call_model)
workflow.add_node("safety_check", check_safety)

# Set the flow
workflow.add_edge(START, "agent")
workflow.add_edge("agent", "safety_check")
workflow.add_conditional_edges("safety_check", should_continue, {
    "tools": "tools_node",
    "end": END
})

# Compile the graph
app = workflow.compile()
