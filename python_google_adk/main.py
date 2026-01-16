from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from human_in_the_loop import auth_tool, confirm_tool_usage

import os

load_dotenv(override=True)


async def main():
    app_name = "my_agent"
    user_id = os.getenv("ARCADE_USER_ID")

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    agent_tools = await get_arcade_tools(
        client, toolkits=["GoogleSheets"]
    )

    for tool in agent_tools:
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="# Introduction

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
        description="An agent that uses GoogleSheets tools provided to perform any task",
        tools=agent_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())