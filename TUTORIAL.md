---
title: "Build a GoogleSheets agent with LangChain (TypeScript) and Arcade"
slug: "ts-langchain-GoogleSheets"
framework: "langchain-ts"
language: "typescript"
toolkits: ["GoogleSheets"]
tools: []
difficulty: "beginner"
generated_at: "2026-03-12T01:34:45Z"
source_template: "ts_langchain"
agent_repo: ""
tags:
  - "langchain"
  - "typescript"
  - "googlesheets"
---

# Build a GoogleSheets agent with LangChain (TypeScript) and Arcade

In this tutorial you'll build an AI agent using [LangChain](https://js.langchain.com/) with [LangGraph](https://langchain-ai.github.io/langgraphjs/) in TypeScript and [Arcade](https://arcade.dev) that can interact with GoogleSheets tools — with built-in authorization and human-in-the-loop support.

## Prerequisites

- The [Bun](https://bun.com) runtime
- An [Arcade](https://arcade.dev) account and API key
- An OpenAI API key

## Project Setup

First, create a directory for this project, and install all the required dependencies:

````bash
mkdir googlesheets-agent && cd googlesheets-agent
bun install @arcadeai/arcadejs @langchain/langgraph @langchain/core langchain chalk
````

## Start the agent script

Create a `main.ts` script, and import all the packages and libraries. Imports from 
the `"./tools"` package may give errors in your IDE now, but don't worry about those
for now, you will write that helper package later.

````typescript
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
````

## Configuration

In `main.ts`, configure your agent's toolkits, system prompt, and model. Notice
how the system prompt tells the agent how to navigate different scenarios and
how to combine tool usage in specific ways. This prompt engineering is important
to build effective agents. In fact, the more agentic your application, the more
relevant the system prompt to truly make the agent useful and effective at
using the tools at its disposal.

````typescript
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
const systemPrompt = "# Agent prompt (for a ReAct-style AI agent that works with Google Sheets)\n\n## Introduction\nYou are an AI ReAct agent that helps users inspect, create, and modify Google Sheets using a fixed set of tools. Use the provided tools to search for spreadsheets, read and write cell values, add notes, create new sheets, and obtain metadata or user context. Operate transparently: always show your reasoning, the tool you plan to use, the parameters you will pass, and then the observation/result returned by the tool. Do not hallucinate spreadsheet ids, sheet names, or tool results \u2014 rely on tool responses.\n\n## Instructions\n- Follow the ReAct interaction pattern. For each step, produce:\n  - Thought: short reasoning about what to do next.\n  - Action: the tool name + JSON parameters you will call.\n  - Observation: the tool output (what the tool returned).\n  - Continue until you have a clear result and then produce a Final Answer for the user.\n- If user input is ambiguous or missing required info (spreadsheet title, sheet name/id, cell coords, etc.), ask a clarifying question before calling tools.\n- Always prefer non-destructive reads first:\n  - Use GoogleSheets_SearchSpreadsheets to locate spreadsheets by title keywords.\n  - Use GoogleSheets_GetSpreadsheetMetadata to list sheet names/ids and confirm sheet positions.\n  - Use GoogleSheets_GetSpreadsheet to read cell values or ranges.\n- Use sheet_id_or_name if available \u2014 it takes precedence over sheet_position.\n- Respect API limits:\n  - GetSpreadsheet: max_rows 1\u20131000 and max_cols 1\u2013100.\n- For writing:\n  - Use GoogleSheets_WriteToCell for single-cell updates.\n  - Use GoogleSheets_UpdateCells for bulk updates (supply data as {row: {col: value}}).\n  - Use GoogleSheets_AddNoteToCell to attach notes (not comments) to a cell.\n  - Use GoogleSheets_CreateSpreadsheet to create a new sheet (optional data may be provided).\n- Use GoogleSheets_WhoAmI if you need the user\u0027s profile or need to confirm the identity/permissions.\n- Error handling:\n  - If an operation returns \"Requested entity was not found\" or a permission error, suggest GoogleSheets_GenerateGoogleFilePickerUrl to let the user select/authorize the file. Offer to retry once the user completes that flow.\n  - If a tool returns unexpected output, report it verbatim and ask the user whether to continue, retry, or use a different approach.\n- Never reveal internal tool-only parameters to end users; show final results in user-friendly terms.\n- For all tool calls include ONLY the parameters required by the tool plus any optional parameters that are necessary (do not send extraneous parameters).\n\n## Action/format conventions (required)\n- For each tool invocation, produce an Action line exactly as:\n  Action: \u003cToolName\u003e\n  Parameters:\n  ```\n  { \"parameter_name\": \u003cvalue\u003e, ... }\n  ```\n- After each Action, wait for the Observation (tool response) and include it verbatim in your chain of reasoning.\n- After completing tasks, provide a concise Final Answer or a short list of the changes performed and their results.\n\nExample (short):\nThought: I should find the spreadsheet the user mentioned.\nAction: GoogleSheets_SearchSpreadsheets\nParameters:\n```\n{ \"spreadsheet_contains\": [\"Budget Q1\"], \"limit\": 5 }\n```\nObservation: (tool output will appear here)\nThought: The search returned 2 matches; ask the user to pick one or proceed with the first.\n... etc.\n\n## Workflows\nBelow are common workflows and the recommended sequence of tools and checks to follow for each. Use the ReAct pattern throughout.\n\n1) Locate a spreadsheet by name (discovery)\n- Purpose: Find spreadsheet id and title when the user gives a title/part of a title.\n- Sequence:\n  - GoogleSheets_SearchSpreadsheets (spreadsheet_contains)\n  - If multiple results: ask user to choose or provide more info\n  - GoogleSheets_GetSpreadsheetMetadata (spreadsheet_id: chosen id) to list sheets and their IDs/positions\n  - Optionally GoogleSheets_GetSpreadsheet (spreadsheet_id, start_row, start_col, max_rows, max_cols) to preview contents\n\n2) Read a specific range or sheet\n- Purpose: Return the contents of a sheet or a range of rows/cols.\n- Sequence:\n  - If spreadsheet unknown: follow Workflow (1)\n  - GoogleSheets_GetSpreadsheetMetadata (spreadsheet_id) to confirm sheet name/id\n  - GoogleSheets_GetSpreadsheet (spreadsheet_id, sheet_id_or_name or sheet_position, start_row, start_col, max_rows, max_cols)\n  - If data is larger than allowed limits, page the reads or ask user to restrict the range.\n\n3) Write a single cell\n- Purpose: Update or set one cell value.\n- Sequence:\n  - If spreadsheet unknown: follow Workflow (1)\n  - Optional: GoogleSheets_GetSpreadsheet to confirm current value\n  - GoogleSheets_WriteToCell\n    Parameters example:\n    ```\n    {\n      \"spreadsheet_id\": \"SPREADSHEET_ID\",\n      \"column\": \"C\",\n      \"row\": 12,\n      \"value\": \"New Value\",\n      \"sheet_name\": \"Sheet1\"   // optional; defaults to Sheet1\n    }\n    ```\n  - Optionally GoogleSheets_AddNoteToCell to annotate the change\n\n4) Update multiple cells / bulk write\n- Purpose: Write multiple cells in one operation.\n- Sequence:\n  - If spreadsheet unknown: follow Workflow (1)\n  - GoogleSheets_UpdateCells\n    Data format example:\n    ```\n    {\n      2: {\"A\": \"Alice\", \"B\": 42},\n      3: {\"A\": \"Bob\", \"B\": 37}\n    }\n    ```\n    (This writes A2, B2, A3, B3.)\n  - Optionally confirm result with GoogleSheets_GetSpreadsheet\n\n5) Add a note to a cell\n- Purpose: Attach a hover-note to a particular cell.\n- Sequence:\n  - If spreadsheet unknown: follow Workflow (1)\n  - Optionally confirm cell exists with GoogleSheets_GetSpreadsheet\n  - GoogleSheets_AddNoteToCell\n    Parameters example:\n    ```\n    {\n      \"spreadsheet_id\": \"SPREADSHEET_ID\",\n      \"column\": \"D\",\n      \"row\": 5,\n      \"note_text\": \"Review this value\",\n      \"sheet_position\": 1  // or sheet_id_or_name\n    }\n    ```\n\n6) Create a new spreadsheet (with initial data)\n- Purpose: Create a new spreadsheet and optionally seed it with data.\n- Sequence:\n  - GoogleSheets_CreateSpreadsheet\n    Example data payload:\n    ```\n    {\n      1: {\"A\": \"Name\", \"B\": \"Score\"},\n      2: {\"A\": \"Alice\", \"B\": 90}\n    }\n    ```\n  - Return the new spreadsheet id and URL from the tool output to the user.\n\n7) When access is denied or file not found (permission \u0026 UX recovery)\n- Purpose: Recover from \"not found\" or permission errors.\n- Sequence:\n  - Suggest GoogleSheets_GenerateGoogleFilePickerUrl to the user and explain they should select the file and grant access.\n  - After the user completes the picker flow, retry the prior call(s).\n- Implementation note: Prompt the user to click the generated URL and then respond when complete. Do not attempt blind retries without user authorization.\n\n8) Confirm user identity / permissions\n- Purpose: Check who you are acting as or confirm permissions.\n- Sequence:\n  - GoogleSheets_WhoAmI\n  - Use returned profile info to explain any permission constraints or to confirm account used.\n\n## Additional guidance and best practices\n- Prefer explicit confirmation with the user before destructive actions (bulk overwrites or deleting content).\n- If the user asks for an operation that requires a sheet name but only a sheet position is provided, explain that sheet_id_or_name takes precedence and request the name or use sheet_position if appropriate.\n- When returning results to the user, summarize what changed and include relevant ids, sheet names, and cell references.\n- Keep tool parameter values exact (column as letter(s) for single-cell tools, row as integer, UpdateCells data as described).\n- If results are large, offer to export to a new spreadsheet (CreateSpreadsheet) and write the data there for easier sharing.\n\n## Example full interaction (pattern)\nThought: The user asked to set C12 in spreadsheet \"Proj Plan\" to \"Done\". I should locate the spreadsheet first.\nAction: GoogleSheets_SearchSpreadsheets\nParameters:\n```\n{ \"spreadsheet_contains\": [\"Proj Plan\"], \"limit\": 10 }\n```\nObservation: (tool output)\nThought: (explain next step based on observation)\nAction: GoogleSheets_GetSpreadsheetMetadata\nParameters:\n```\n{ \"spreadsheet_id\": \"THE_CHOSEN_ID\" }\n```\nObservation: (tool output)\nThought: Confirm existing cell value then write.\nAction: GoogleSheets_GetSpreadsheet\nParameters:\n```\n{ \"spreadsheet_id\": \"THE_CHOSEN_ID\", \"start_row\": 12, \"start_col\": \"C\", \"max_rows\": 1, \"max_cols\": 1 }\n```\nObservation: (tool output)\nThought: Now update the cell.\nAction: GoogleSheets_WriteToCell\nParameters:\n```\n{\n  \"spreadsheet_id\": \"THE_CHOSEN_ID\",\n  \"column\": \"C\",\n  \"row\": 12,\n  \"value\": \"Done\",\n  \"sheet_name\": \"Sheet1\"\n}\n```\nObservation: (tool output)\nFinal Answer: I updated cell C12 in \"Proj Plan\" to \"Done\". (Include spreadsheet id, sheet name/position, and any note.)\n\nUse this prompt as the agent\u0027s instruction set. Always adhere to the ReAct trace format and rely on the tool outputs for facts.";
// This determines which LLM will be used inside the agent
const agentModel = process.env.OPENAI_MODEL;
if (!agentModel) {
  throw new Error("Missing OPENAI_MODEL. Add it to your .env file.");
}
// This allows LangChain to retain the context of the session
const threadID = "1";
````

Set the following environment variables in a `.env` file:

````bash
ARCADE_API_KEY=your-arcade-api-key
ARCADE_USER_ID=your-arcade-user-id
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
````

## Implementing the `tools.ts` module

The `tools.ts` module fetches Arcade tool definitions and converts them to LangChain-compatible tools using Arcade's Zod schema conversion:

### Create the file and import the dependencies

Create a `tools.ts` file, and add import the following. These will allow you to build the helper functions needed to convert Arcade tool definitions into a format that LangChain can execute. Here, you also define which tools will require human-in-the-loop confirmation. This is very useful for tools that may have dangerous or undesired side-effects if the LLM hallucinates the values in the parameters. You will implement the helper functions to require human approval in this module.

````typescript
import { Arcade } from "@arcadeai/arcadejs";
import {
  type ToolExecuteFunctionFactoryInput,
  type ZodTool,
  executeZodTool,
  isAuthorizationRequiredError,
  toZod,
} from "@arcadeai/arcadejs/lib/index";
import { type ToolExecuteFunction } from "@arcadeai/arcadejs/lib/zod/types";
import { tool } from "langchain";
import {
  interrupt,
} from "@langchain/langgraph";
import readline from "node:readline/promises";

// This determines which tools require human in the loop approval to run
const TOOLS_WITH_APPROVAL = ['GoogleSheets_AddNoteToCell', 'GoogleSheets_CreateSpreadsheet', 'GoogleSheets_UpdateCells', 'GoogleSheets_WriteToCell'];
````

### Create a confirmation helper for human in the loop

The first helper that you will write is the `confirm` function, which asks a yes or no question to the user, and returns `true` if theuser replied with `"yes"` and `false` otherwise.

````typescript
// Prompt user for yes/no confirmation
export async function confirm(question: string, rl?: readline.Interface): Promise<boolean> {
  let shouldClose = false;
  let interface_ = rl;

  if (!interface_) {
      interface_ = readline.createInterface({
          input: process.stdin,
          output: process.stdout,
      });
      shouldClose = true;
  }

  const answer = await interface_.question(`${question} (y/n): `);

  if (shouldClose) {
      interface_.close();
  }

  return ["y", "yes"].includes(answer.trim().toLowerCase());
}
````

Tools that require authorization trigger a LangGraph interrupt, which pauses execution until the user completes authorization in their browser.

### Create the execution helper

This is a wrapper around the `executeZodTool` function. Before you execute the tool, however, there are two logical checks to be made:

1. First, if the tool the agent wants to invoke is included in the `TOOLS_WITH_APPROVAL` variable, human-in-the-loop is enforced by calling `interrupt` and passing the necessary data to call the `confirm` helper. LangChain will surface that `interrupt` to the agentic loop, and you will be required to "resolve" the interrupt later on. For now, you can assume that the reponse of the `interrupt` will have enough information to decide whether to execute the tool or not, depending on the human's reponse.
2. Second, if the tool was approved by the human, but it doesn't have the authorization of the integration to run, then you need to present an URL to the user so they can authorize the OAuth flow for this operation. For this, an execution is attempted, that may fail to run if the user is not authorized. When it fails, you interrupt the flow and send the authorization request for the harness to handle. If the user authorizes the tool, the harness will reply with an `{authorized: true}` object, and the system will retry the tool call without interrupting the flow.

````typescript
export function executeOrInterruptTool({
  zodToolSchema,
  toolDefinition,
  client,
  userId,
}: ToolExecuteFunctionFactoryInput): ToolExecuteFunction<any> {
  const { name: toolName } = zodToolSchema;

  return async (input: unknown) => {
    try {

      // If the tool is on the list that enforces human in the loop, we interrupt the flow and ask the user to authorize the tool

      if (TOOLS_WITH_APPROVAL.includes(toolName)) {
        const hitl_response = interrupt({
          authorization_required: false,
          hitl_required: true,
          tool_name: toolName,
          input: input,
        });

        if (!hitl_response.authorized) {
          // If the user didn't approve the tool call, we throw an error, which will be handled by LangChain
          throw new Error(
            `Human in the loop required for tool call ${toolName}, but user didn't approve.`
          );
        }
      }

      // Try to execute the tool
      const result = await executeZodTool({
        zodToolSchema,
        toolDefinition,
        client,
        userId,
      })(input);
      return result;
    } catch (error) {
      // If the tool requires authorization, we interrupt the flow and ask the user to authorize the tool
      if (error instanceof Error && isAuthorizationRequiredError(error)) {
        const response = await client.tools.authorize({
          tool_name: toolName,
          user_id: userId,
        });

        // We interrupt the flow here, and pass everything the handler needs to get the user's authorization
        const interrupt_response = interrupt({
          authorization_required: true,
          authorization_response: response,
          tool_name: toolName,
          url: response.url ?? "",
        });

        // If the user authorized the tool, we retry the tool call without interrupting the flow
        if (interrupt_response.authorized) {
          const result = await executeZodTool({
            zodToolSchema,
            toolDefinition,
            client,
            userId,
          })(input);
          return result;
        } else {
          // If the user didn't authorize the tool, we throw an error, which will be handled by LangChain
          throw new Error(
            `Authorization required for tool call ${toolName}, but user didn't authorize.`
          );
        }
      }
      throw error;
    }
  };
}
````

### Create the tool retrieval helper

The last helper function of this module is the `getTools` helper. This function will take the configurations you defined in the `main.ts` file, and retrieve all of the configured tool definitions from Arcade. Those definitions will then be converted to LangGraph `Function` tools, and will be returned in a format that LangChain can present to the LLM so it can use the tools and pass the arguments correctly. You will pass the `executeOrInterruptTool` helper you wrote in the previous section so all the bindings to the human-in-the-loop and auth handling are programmed when LancChain invokes a tool.


````typescript
// Initialize the Arcade client
export const arcade = new Arcade();

export type GetToolsProps = {
  arcade: Arcade;
  toolkits?: string[];
  tools?: string[];
  userId: string;
  limit?: number;
}


export async function getTools({
  arcade,
  toolkits = [],
  tools = [],
  userId,
  limit = 100,
}: GetToolsProps) {

  if (toolkits.length === 0 && tools.length === 0) {
      throw new Error("At least one tool or toolkit must be provided");
  }

  // Todo(Mateo): Add pagination support
  const from_toolkits = await Promise.all(toolkits.map(async (tkitName) => {
      const definitions = await arcade.tools.list({
          toolkit: tkitName,
          limit: limit
      });
      return definitions.items;
  }));

  const from_tools = await Promise.all(tools.map(async (toolName) => {
      return await arcade.tools.get(toolName);
  }));

  const all_tools = [...from_toolkits.flat(), ...from_tools];
  const unique_tools = Array.from(
      new Map(all_tools.map(tool => [tool.qualified_name, tool])).values()
  );

  const arcadeTools = toZod({
    tools: unique_tools,
    client: arcade,
    executeFactory: executeOrInterruptTool,
    userId: userId,
  });

  // Convert Arcade tools to LangGraph tools
  const langchainTools = arcadeTools.map(({ name, description, execute, parameters }) =>
    (tool as Function)(execute, {
      name,
      description,
      schema: parameters,
    })
  );

  return langchainTools;
}
````

## Building the Agent

Back on the `main.ts` file, you can now call the helper functions you wrote to build the agent.

### Retrieve the configured tools

Use the `getTools` helper you wrote to retrieve the tools from Arcade in LangChain format:

````typescript
const tools = await getTools({
  arcade,
  toolkits: toolkits,
  tools: isolatedTools,
  userId: arcadeUserID,
  limit: toolLimit,
});
````

### Write an interrupt handler

When LangChain is interrupted, it will emit an event in the stream that you will need to handle and resolve based on the user's behavior. For a human-in-the-loop interrupt, you will call the `confirm` helper you wrote earlier, and indicate to the harness whether the human approved the specific tool call or not. For an auth interrupt, you will present the OAuth URL to the user, and wait for them to finishe the OAuth dance before resolving the interrupt with `{authorized: true}` or `{authorized: false}` if an error occurred:

````typescript
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
````

### Create an Agent instance

Here you create the agent using the `createAgent` function. You pass the system prompt, the model, the tools, and the checkpointer. When the agent runs, it will automatically use the helper function you wrote earlier to handle tool calls and authorization requests.

````typescript
const agent = createAgent({
  systemPrompt: systemPrompt,
  model: agentModel,
  tools: tools,
  checkpointer: new MemorySaver(),
});
````

### Write the invoke helper

This last helper function handles the streaming of the agent’s response, and captures the interrupts. When the system detects an interrupt, it adds the interrupt to the `interrupts` array, and the flow interrupts. If there are no interrupts, it will just stream the agent’s to your console.

````typescript
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
````

### Write the main function

Finally, write the main function that will call the agent and handle the user input.

Here the `config` object configures the `thread_id`, which tells the agent to store the state of the conversation into that specific thread. Like any typical agent loop, you:

1. Capture the user input
2. Stream the agent's response
3. Handle any authorization interrupts
4. Resume the agent after authorization
5. Handle any errors
6. Exit the loop if the user wants to quit

````typescript
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
````

## Running the Agent

### Run the agent

```bash
bun run main.ts
```

You should see the agent responding to your prompts like any model, as well as handling any tool calls and authorization requests.

## Next Steps

- Clone the [repository](https://github.com/arcade-agents/ts-langchain-GoogleSheets) and run it
- Add more toolkits to the `toolkits` array to expand capabilities
- Customize the `systemPrompt` to specialize the agent's behavior
- Explore the [Arcade documentation](https://docs.arcade.dev) for available toolkits

