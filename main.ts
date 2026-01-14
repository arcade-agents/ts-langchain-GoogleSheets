"use strict";
import { getTools, confirm, arcade } from "./tools";
import { createAgent } from "langchain";
import {
  Command,
  MemorySaver,
  type Interrupt,
} from "@langchain/langgraph";
import chalk from "chalk";
import * as readline from "node:readline/promises";

// configure your own values to customize your agent

// The Arcade User ID identifies who is authorizing each service.
const arcadeUserID = process.env.ARCADE_USER_ID;
if (!arcadeUserID) {
  throw new Error("Missing ARCADE_USER_ID. Add it to your .env file.");
}
// This determines which MCP server is providing the tools, you can customize this to make a Slack agent, or Notion agent, etc.
// all tools from each of these MCP servers will be retrieved from arcade
const toolkits=['GoogleSheets'];
// This determines isolated tools that will be
const isolatedTools=[];
// This determines the maximum number of tool definitions Arcade will return
const toolLimit = 100;
// This prompt defines the behavior of the agent.
const systemPrompt = `# Introduction

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

This workflow set will empower the Google Sheets AI Agent to operate efficiently, providing the necessary tools and steps at every stage of the user's interaction with Google Sheets.`;
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";

const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});



async function handleInterrupt(
  interrupt: Interrupt,
  rl: readline.Interface
): Promise<{ authorized: boolean }> {
  const value = interrupt.value;
  const authorization_required = value.authorization_required;
  const hitl_required = value.hitl_required;
  if (authorization_required) {
    const tool_name = value.tool_name;
    const authorization_response = value.authorization_response;
    console.log("⚙️: Authorization required for tool call", tool_name);
    console.log(
      "⚙️: Please authorize in your browser",
      authorization_response.url
    );
    console.log("⚙️: Waiting for you to complete authorization...");
    try {
      await arcade.auth.waitForCompletion(authorization_response.id);
      console.log("⚙️: Authorization granted. Resuming execution...");
      return { authorized: true };
    } catch (error) {
      console.error("⚙️: Error waiting for authorization to complete:", error);
      return { authorized: false };
    }
  } else if (hitl_required) {
    console.log("⚙️: Human in the loop required for tool call", value.tool_name);
    console.log("⚙️: Please approve the tool call", value.input);
    const approved = await confirm("Do you approve this tool call?", rl);
    return { authorized: approved };
  }
  return { authorized: false };
}

const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});

async function streamAgent(
  agent: any,
  input: any,
  config: any
): Promise<Interrupt[]> {
  const stream = await agent.stream(input, {
    ...config,
    streamMode: "updates",
  });
  const interrupts: Interrupt[] = [];

  for await (const chunk of stream) {
    if (chunk.__interrupt__) {
      interrupts.push(...(chunk.__interrupt__ as Interrupt[]));
      continue;
    }
    for (const update of Object.values(chunk)) {
      for (const msg of (update as any)?.messages ?? []) {
        console.log("🤖: ", msg.toFormattedString());
      }
    }
  }

  return interrupts;
}

async function main() {
  const config = { configurable: { thread_id: threadID } };
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  console.log(chalk.green("Welcome to the chatbot! Type 'exit' to quit."));
  while (true) {
    const input = await rl.question("> ");
    if (input.toLowerCase() === "exit") {
      break;
    }
    rl.pause();

    try {
      let agentInput: any = {
        messages: [{ role: "user", content: input }],
      };

      // Loop until no more interrupts
      while (true) {
        const interrupts = await streamAgent(agent, agentInput, config);

        if (interrupts.length === 0) {
          break; // No more interrupts, we're done
        }

        // Handle all interrupts
        const decisions: any[] = [];
        for (const interrupt of interrupts) {
          decisions.push(await handleInterrupt(interrupt, rl));
        }

        // Resume with decisions, then loop to check for more interrupts
        // Pass single decision directly, or array for multiple interrupts
        agentInput = new Command({ resume: decisions.length === 1 ? decisions[0] : decisions });
      }
    } catch (error) {
      console.error(error);
    }

    rl.resume();
  }
  console.log(chalk.red("👋 Bye..."));
  process.exit(0);
}

// Run the main function
main().catch((err) => console.error(err));