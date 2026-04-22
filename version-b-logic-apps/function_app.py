import azure.functions as func
import json

app = func.FunctionApp()

@app.function_name(name="ValidateExpenseFunction")
@app.route(route="validate-expense", methods=["POST"])
def validate_expense(req: func.HttpRequest):

    import json

    data = req.get_json()

    required_fields = [
        "employee_name",
        "employee_email",
        "amount",
        "category",
        "description",
        "manager_email"
    ]

    for field in required_fields:
        if field not in data or not data[field]:
            return func.HttpResponse(
                json.dumps({"valid": False, "reason": f"Missing {field}"}),
                status_code=200,
                mimetype="application/json"
            )

    valid_categories = ["travel", "meals", "supplies", "equipment", "software", "other"]

    if data["category"] not in valid_categories:
        return func.HttpResponse(
            json.dumps({"valid": False, "reason": "Invalid category"}),
            status_code=200,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({"valid": True}),
        status_code=200,
        mimetype="application/json"
    )