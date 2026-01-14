# An agent that uses GoogleSheets tools provided to perform any task

## Purpose

# Introduction

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

This workflow set will empower the Google Sheets AI Agent to operate efficiently, providing the necessary tools and steps at every stage of the user's interaction with Google Sheets.

## MCP Servers

The agent uses tools from these Arcade MCP Servers:

- GoogleSheets

## Human-in-the-Loop Confirmation

The following tools require human confirmation before execution:

- `GoogleSheets_CreateSpreadsheet`
- `GoogleSheets_UpdateCells`
- `GoogleSheets_WriteToCell`


## Getting Started

1. Install dependencies:
    ```bash
    bun install
    ```

2. Set your environment variables:

    Copy the `.env.example` file to create a new `.env` file, and fill in the environment variables.
    ```bash
    cp .env.example .env
    ```

3. Run the agent:
    ```bash
    bun run main.ts
    ```