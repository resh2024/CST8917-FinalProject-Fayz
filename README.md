# CST8917 Final Project — Expense Approval Workflow Comparison

**Name:** Fayz Reshid  
**Student Number:** 041066116  
**Course:** CST8917 — Serverless Applications  
**Project:** Dual Implementation of Expense Approval Workflow  
**Date:** April 21, 2026

---

# Overview

This project implements the same expense approval workflow using two different Azure serverless approaches:

- Version A: Azure Durable Functions (code-first orchestration)
- Version B: Azure Logic Apps + Service Bus (visual orchestration)

The goal was to compare both approaches based on development experience, testing, error handling, and overall practicality.

---

# Version A — Durable Functions

## Summary

Version A was built using Azure Durable Functions in Python. The workflow is fully code-driven and uses an orchestrator to manage the entire process. Activities were used for validation and sending email notifications, while a timer and external event were used to simulate manager approval.

The workflow handles:

- Input validation
- Auto-approval for expenses under $100
- Manager approval for expenses over $100
- Timeout handling using durable timers
- Final email notification to the employee

## Design Decisions

I chose Durable Functions because it made the workflow logic easier to control in code. Using an orchestrator gave me full visibility over each step, and it was easier to manage complex logic like waiting for external approval.

I also used:

- Activity functions for validation and email
- External events for manager approval
- Timer-based escalation when no response is received

## Challenges

The main challenges were:

- Getting the orchestration pattern working correctly
- Handling JSON input properly between activities
- Debugging errors when the function app wouldn’t index properly
- Understanding how external events and timers work together

Once it was set up correctly, the workflow became very predictable and easy to test.

---

# Version B — Logic Apps + Service Bus

## Summary

Version B used Azure Logic Apps combined with Service Bus queues and topics. Messages are sent to a queue, processed by a Logic App, validated using an Azure Function, and then routed based on conditions.

The workflow includes:

- Service Bus queue for incoming requests
- Logic App for orchestration
- HTTP-triggered Azure Function for validation
- Service Bus topic for output routing (approved, rejected, escalated)
- Email notifications sent to employees

## Approach for Manager Approval

Since Logic Apps does not support real external event-based waiting like Durable Functions, I simulated the manager approval step using a delay. If no response is received within the delay period, the request is automatically escalated.

This was not as clean as Durable Functions, but it worked for demonstrating the workflow.

## Challenges

The biggest issues were:

- Authentication problems with Service Bus connections
- Logic App trigger skipping messages when queue was empty
- Confusion around “Send message to topic” configuration
- HTTP errors when the Azure Function URL was not correctly deployed
- Debugging failed runs due to token expiry and connection issues

Compared to Durable Functions, Logic Apps required more setup in the Azure portal and was more sensitive to configuration mistakes.

---

# Comparison Analysis

## Development Experience

Durable Functions felt more natural for building this kind of workflow because everything is written in code. I could clearly see the flow of execution inside the orchestrator, and it was easier to reason about the logic.

Logic Apps, on the other hand, was faster to start visually but became harder to manage as the workflow grew. Clicking through different steps in the portal was less efficient than just reading code.

Overall, Durable Functions gave me more confidence that the logic was correct, especially when dealing with branching and external events.

---

## Testability

Testing Durable Functions locally was more straightforward because I could use HTTP triggers and test inputs directly through the terminal. I could also replay orchestrations which helped with debugging.

Logic Apps was harder to test consistently. Sometimes messages were skipped or delayed, and I had to rely on the Azure portal run history instead of local testing.

Durable Functions was clearly better for repeatable and controlled testing.

---

## Error Handling

Durable Functions gave more control over error handling using try/catch patterns in code and built-in retry behavior for activities.

Logic Apps handled errors automatically in some cases, but it was less predictable. When something failed, it was not always obvious where the issue occurred unless I checked each step in the run history.

Durable Functions felt more reliable for debugging and recovery logic.

---

## Human Interaction Pattern

Durable Functions handled the manager approval step much better using external events and timers. This made it feel like a real workflow waiting for input.

In Logic Apps, I had to simulate this using a delay, which is not truly event-driven. This made the Logic Apps version less realistic for human approval scenarios.

Durable Functions is clearly better suited for long-running approval workflows.

---

## Observability

Logic Apps had a better visual interface for seeing each step of execution. The run history made it easy to click through and inspect inputs and outputs.

Durable Functions required more effort to debug since logs are mostly in Application Insights or local console output.

So in terms of visibility, Logic Apps was easier to follow.

---

## Cost

At a small scale (around 100 expenses per day), both solutions would be relatively cheap. Logic Apps may be slightly more expensive due to per-action billing.

At a larger scale (around 10,000 expenses per day), Durable Functions would likely be more cost-efficient because execution is more lightweight and event-driven.

Logic Apps costs would increase due to each action being billed separately.

---

## Recommendation

If I had to choose one approach for production, I would pick Durable Functions for this specific workflow.

The main reason is control. The workflow involves branching logic, validation, and waiting for human approval, which Durable Functions handles very naturally. It is easier to test, debug, and maintain as code.

However, I would still use Logic Apps in cases where:

- The workflow is simple
- Integration with many external services is needed
- A non-developer team needs to maintain it visually

So overall, Durable Functions is better for complex backend workflows, while Logic Apps is better for quick integration-based automation.

---

# References

- Azure Durable Functions Documentation  
  https://learn.microsoft.com/en-us/azure/azure-functions/durable/durable-functions-overview

- Azure Logic Apps Documentation  
  https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-overview

- Azure Service Bus Documentation  
  https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-messaging-overview

- Azure Functions HTTP Triggers  
  https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-http-webhook

---

# AI Disclosure

AI tools were used to help structure the README and improve clarity of writing and understanding certain concepts as well as some code generation. Code implementation, testing, and deployment work was done manually as part of the assignment requirements.
