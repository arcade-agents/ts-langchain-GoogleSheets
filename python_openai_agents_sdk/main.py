from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,)
from functools import partial
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from human_in_the_loop import (UserDeniedToolCall,
                               confirm_tool_usage,
                               auth_tool)

import globals


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self,
                       context: RunContextWrapper,
                       agent: Agent) -> None:
        self.event_counter += 1
        print(f"### ({self.display_name}) {
              self.event_counter}: Agent {agent.name} started")

    async def on_end(self,
                     context: RunContextWrapper,
                     agent: Agent,
                     output: Any) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended with output {output}"
                agent.name} ended"
        )

    async def on_handoff(self,
                         context: RunContextWrapper,
                         agent: Agent,
                         source: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                source.name} handed off to {agent.name}"
        )

    async def on_tool_start(self,
                            context: RunContextWrapper,
                            agent: Agent,
                            tool: Tool) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}:"
            f" Agent {agent.name} started tool {tool.name}"
            f" with context: {context.context}"
        )

    async def on_tool_end(self,
                          context: RunContextWrapper,
                          agent: Agent,
                          tool: Tool,
                          result: str) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended tool {tool.name} with result {result}"
                agent.name} ended tool {tool.name}"
        )


async def main():

    context = {
        "user_id": os.getenv("ARCADE_USER_ID"),
    }

    client = AsyncArcade()

    arcade_tools = await get_arcade_tools(
        client, toolkits=["GoogleSheets"]
    )

    for tool in arcade_tools:
        # - human in the loop
        if tool.name in ENFORCE_HUMAN_CONFIRMATION:
            tool.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=tool.name,
                callback=tool.on_invoke_tool,
            )
        # - auth
        await auth_tool(client, tool.name, user_id=context["user_id"])

    agent = Agent(
        name="",
        instructions="# Introduction

Welcome to the Google Sheets AI Agent! This agent is designed to assist you in interacting with Google Sheets seamlessly. Whether you need to create a new spreadsheet, update cells, add notes, or retrieve data, this agent can handle it with ease. Leveraging various Google Sheets tools, it aims to enhance your productivity and streamline your workflow.

# Instructions

1. **User Input:** The agent will prompt the user for necessary information based on the requested action (e.g., title for creating a spreadsheet, cell references for updating or adding notes).
2. **Validation:** It will validate the inputs to ensure they meet the requirements for each tool.
3. **Execution:** The agent will execute the appropriate tools in the specified order to achieve the user's request.
4. **Confirmation:** After completing the tasks, the agent will confirm the actions taken and provide relevant information such as generated spreadsheet IDs or updated cell contents.
5. **Error Handling:** If issues arise (e.g., access denied, file not found), the agent will gracefully handle errors and suggest using the Google File Picker if necessary.

# Workflows

## 1. Create a New Spreadsheet
- **Input:** Title, initial data (optional).
- **Tools:**
  1. `GoogleSheets_CreateSpreadsheet` to create a new spreadsheet.

## 2. Update Cells
- **Input:** Spreadsheet ID, cell references (column and row), value.
- **Tools:**
  1. `GoogleSheets_WriteToCell` to write a value to a specific cell.

## 3. Add Notes to Cells
- **Input:** Spreadsheet ID, cell references (column and row), note text.
- **Tools:**
  1. `GoogleSheets_AddNoteToCell` to add a note to a specific cell.

## 4. Retrieve Data from Spreadsheet
- **Input:** Spreadsheet ID, optional sheet position, start row, start column, maximum rows and columns to fetch.
- **Tools:**
  1. `GoogleSheets_GetSpreadsheet` to retrieve data from the specified range.

## 5. Get Spreadsheet Metadata
- **Input:** Spreadsheet ID.
- **Tools:**
  1. `GoogleSheets_GetSpreadsheetMetadata` to retrieve metadata about the spreadsheet.

## 6. Search for Spreadsheets
- **Input:** Keywords to search for (include or exclude), limit on results.
- **Tools:**
  1. `GoogleSheets_SearchSpreadsheets` to find spreadsheets in the user's Google Drive.

## 7. User Profile Information
- **Input:** None.
- **Tools:**
  1. `GoogleSheets_WhoAmI` to get comprehensive user profile and environment information.

This workflow set will empower the Google Sheets AI Agent to operate efficiently, providing the necessary tools and steps at every stage of the user's interaction with Google Sheets.",
        model=os.environ["OPENAI_MODEL"],
        tools=arcade_tools,
        hooks=CustomAgentHooks(display_name="")
    )

    # initialize the conversation
    history: list[TResponseInputItem] = []
    # run the loop!
    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=history,
                context=context
            )
            history = result.to_input_list()
            print(result.final_output)
        except UserDeniedToolCall as e:
            history.extend([
                {"role": "assistant",
                 "content": f"Please confirm the call to {e.tool_name}"},
                {"role": "user",
                 "content": "I changed my mind, please don't do it!"},
                {"role": "assistant",
                 "content": f"Sure, I cancelled the call to {e.tool_name}."
                 " What else can I do for you today?"
                 },
            ])
            print(history[-1]["content"])

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())