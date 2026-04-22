import azure.functions as func
import azure.durable_functions as df
from datetime import timedelta
import json
import logging

app = func.FunctionApp()

# Valid expense categories
VALID_CATEGORIES = {"travel", "meals", "supplies", "equipment", "software", "other"}
APPROVAL_THRESHOLD = 100.00
TIMEOUT_MINUTES = 5  # Short for testing; increase for production


# ============================================================
# CLIENT FUNCTION: HTTP trigger to start the workflow
# ============================================================
@app.route(route="expense", methods=["POST"])
@app.durable_client_input(client_name="client")
async def submit_expense(req: func.HttpRequest, client: df.DurableOrchestrationClient):
    """HTTP endpoint to submit a new expense request."""
    try:
        expense_data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )
    
    # Start the orchestrator
    instance_id = await client.start_new("expense_orchestrator", client_input=expense_data)
    
    logging.info(f"Started orchestration with ID = {instance_id}")
    
    # Return URLs for checking status and sending approval/rejection
    return client.create_check_status_response(req, instance_id)


# ============================================================
# CLIENT FUNCTION: HTTP trigger for manager approval/rejection
# ============================================================
@app.route(route="expense/{instance_id}/decision", methods=["POST"])
@app.durable_client_input(client_name="client")
async def manager_decision(req: func.HttpRequest, client: df.DurableOrchestrationClient):
    """HTTP endpoint for manager to approve or reject an expense."""
    instance_id = req.route_params.get("instance_id")
    
    try:
        body = req.get_json()
        decision = body.get("decision", "").lower()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json"
        )
    
    if decision not in ["approve", "reject"]:
        return func.HttpResponse(
            json.dumps({"error": "Decision must be 'approve' or 'reject'"}),
            status_code=400,
            mimetype="application/json"
        )
    
    # Raise the event to the waiting orchestrator
    await client.raise_event(instance_id, "ManagerDecision", decision)
    
    return func.HttpResponse(
        json.dumps({"message": f"Decision '{decision}' sent for instance {instance_id}"}),
        status_code=200,
        mimetype="application/json"
    )


# ============================================================
# ORCHESTRATOR FUNCTION: Coordinates the workflow
# ============================================================
@app.orchestration_trigger(context_name="context")
def expense_orchestrator(context: df.DurableOrchestrationContext):
    """Main orchestrator implementing the expense approval workflow."""
    expense_data = context.get_input()
    
    # Step 1: Validate the expense
    validation_result = yield context.call_activity("validate_expense", expense_data)
    
    if not validation_result["is_valid"]:
        # Validation failed — notify and end
        yield context.call_activity("send_notification", {
            "email": expense_data.get("employee_email", ""),
            "employee_name": expense_data.get("employee_name", "Employee"),
            "status": "rejected",
            "reason": validation_result["error"],
            "expense": expense_data
        })
        return {"status": "validation_failed", "error": validation_result["error"]}
    
    amount = float(expense_data.get("amount", 0))
    
    # Step 2: Check if auto-approval applies
    if amount < APPROVAL_THRESHOLD:
        # Auto-approve
        yield context.call_activity("send_notification", {
            "email": expense_data.get("employee_email"),
            "employee_name": expense_data.get("employee_name"),
            "status": "approved",
            "reason": "Auto-approved (under $100)",
            "expense": expense_data
        })
        return {"status": "approved", "method": "auto"}
    
    # Step 3: Human interaction pattern — wait for manager decision with timeout
    # Send approval request to manager
    yield context.call_activity("request_manager_approval", {
        "manager_email": expense_data.get("manager_email"),
        "employee_name": expense_data.get("employee_name"),
        "amount": amount,
        "category": expense_data.get("category"),
        "description": expense_data.get("description"),
        "instance_id": context.instance_id
    })
    
    # Set up the timer for timeout
    timeout = context.current_utc_datetime + timedelta(minutes=TIMEOUT_MINUTES)
    timeout_task = context.create_timer(timeout)
    
    # Wait for either manager decision or timeout
    decision_task = context.wait_for_external_event("ManagerDecision")
    
    yield context.task_any([decision_task, timeout_task])
    
    if decision_task.is_completed:
        # Manager responded in time — cancel the timer
        timeout_task.cancel()
        decision = decision_task.result
        
        if decision == "approve":
            status = "approved"
            reason = "Manager approved"
        else:
            status = "rejected"
            reason = "Manager rejected"
    else:
        # Timeout fired first — escalate and auto-approve
        status = "escalated"
        reason = "No manager response — auto-approved with escalation"
    
    # Step 4: Send final notification
    yield context.call_activity("send_notification", {
        "email": expense_data.get("employee_email"),
        "employee_name": expense_data.get("employee_name"),
        "status": status,
        "reason": reason,
        "expense": expense_data
    })
    
    return {"status": status, "reason": reason}


# ============================================================
# ACTIVITY FUNCTIONS
# ============================================================
@app.activity_trigger(input_name="expense")
def validate_expense(expense: dict) -> dict:
    """Validates the expense request."""
    required_fields = ["employee_name", "employee_email", "amount", "category", "description", "manager_email"]
    
    # Check for missing fields
    missing = [field for field in required_fields if not expense.get(field)]
    if missing:
        return {"is_valid": False, "error": f"Missing required fields: {', '.join(missing)}"}
    
    # Validate category
    category = expense.get("category", "").lower()
    if category not in VALID_CATEGORIES:
        return {"is_valid": False, "error": f"Invalid category '{category}'. Valid categories: {', '.join(VALID_CATEGORIES)}"}
    
    # Validate amount is a positive number
    try:
        amount = float(expense.get("amount"))
        if amount <= 0:
            return {"is_valid": False, "error": "Amount must be positive"}
    except (ValueError, TypeError):
        return {"is_valid": False, "error": "Amount must be a valid number"}
    
    return {"is_valid": True}


@app.activity_trigger(input_name="activitypayload")
def request_manager_approval(activitypayload: dict) -> str:
    """Sends approval request to the manager."""
    # In a real implementation, send an email to the manager with approve/reject links
    # For this project, we'll log it and rely on the HTTP endpoint for decisions
    logging.info(
        f"Manager approval requested: {activitypayload['manager_email']} for "
        f"${activitypayload['amount']} ({activitypayload['category']}) from {activitypayload['employee_name']}. "
        f"Instance ID: {activitypayload['instance_id']}"
    )
    
    # You could integrate with Azure Communication Services or SendGrid here
    # to send an actual email with links to the decision endpoint
    
    return "Approval request sent"


@app.activity_trigger(input_name="activitypayload")
def send_notification(activitypayload: dict) -> str:
    """Sends notification email to the employee."""
    email = activitypayload.get("email")
    employee_name = activitypayload.get("employee_name")
    status = activitypayload.get("status")
    reason = activitypayload.get("reason")
    expense = activitypayload.get("expense", {})
    
    # Log the notification (replace with actual email sending)
    logging.info(
        f"NOTIFICATION to {email}:\n"
        f"  Dear {employee_name},\n"
        f"  Your expense request for ${expense.get('amount')} ({expense.get('category')}) "
        f"has been {status.upper()}.\n"
        f"  Reason: {reason}"
    )
    
    # TODO: Integrate with Azure Communication Services or SendGrid
    # Example with Azure Communication Services:
    # from azure.communication.email import EmailClient
    # email_client = EmailClient.from_connection_string(os.environ["EMAIL_CONNECTION_STRING"])
    # message = {...}
    # email_client.begin_send(message)
    
    return f"Notification sent to {email}"
