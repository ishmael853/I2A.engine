from i2a.execution.result import ActionResult, WorkflowExecutionResult

def test_successful_action_result():
    result = ActionResult(
        step_id="step_1",
        action="open_url",
        success=True,
        message="Website opened successfully.",
    )

    assert result.success is True
    assert result.step_id == "step_1"

def test_failed_action_result():
    result = ActionResult(
        step_id="step_2",
        action="wait",
        success=False,
        message="Action failed.",
        error="Unexpected error.",
    )

    assert result.success is False
    assert result.error == "Unexpected error."

def test_workflow_execution_counts():
    results = [
        ActionResult("step_1", "open_url", True, "Completed."),
        ActionResult("step_2", "wait", True, "Completed."),
        ActionResult("step_3", "wait", False, "Failed."),
    ]

    workflow = WorkflowExecutionResult(
        workflow_name="Test workflow",
        success=False,
        results=results,
    )

    assert workflow.total_steps == 3
    assert workflow.successful_steps == 2
    assert workflow.failed_steps == 1

def test_result_to_dict():
    result = ActionResult(
        step_id="step_1",
        action="wait",
        success=True,
        message="Completed.",
    )

    data = result.to_dict()

    assert data["action"] == "wait"
    assert data["success"] is True