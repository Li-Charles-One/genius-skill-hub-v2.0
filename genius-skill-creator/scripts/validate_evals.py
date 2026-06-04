#!/usr/bin/env python3
"""
Validate genius-skill-creator eval definitions.
"""

import argparse
import json
import sys
from pathlib import Path

ASSERTION_TYPES = {"contains", "not_contains", "file_exists", "exit_code"}


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_assertion(assertion, eval_id, index, errors):
    prefix = f"{eval_id}.assertions[{index}]"
    require(isinstance(assertion, dict), f"{prefix}: must be an object", errors)
    if not isinstance(assertion, dict):
        return

    assertion_type = assertion.get("type")
    require(assertion_type in ASSERTION_TYPES, f"{prefix}: unsupported type {assertion_type!r}", errors)

    if assertion_type in {"contains", "not_contains"}:
        value = assertion.get("value")
        require(isinstance(value, str) and bool(value.strip()), f"{prefix}: value must be non-empty text", errors)
    elif assertion_type == "file_exists":
        path = assertion.get("path")
        require(isinstance(path, str) and bool(path.strip()), f"{prefix}: path must be non-empty text", errors)
    elif assertion_type == "exit_code":
        command = assertion.get("command")
        value = assertion.get("value")
        require(isinstance(command, str) and bool(command.strip()), f"{prefix}: command must be non-empty text", errors)
        require(isinstance(value, int), f"{prefix}: value must be an integer exit code", errors)


def validate_evals(path):
    path = Path(path)
    errors = []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"Invalid JSON: {exc}"]

    require(isinstance(data, dict), "Root must be an object", errors)
    if not isinstance(data, dict):
        return False, errors

    require(isinstance(data.get("skill_name"), str) and data["skill_name"].strip(), "skill_name must be non-empty text", errors)
    evals = data.get("evals")
    require(isinstance(evals, list) and bool(evals), "evals must be a non-empty list", errors)
    if not isinstance(evals, list):
        return False, errors

    seen_ids = set()
    trigger_count = 0
    non_trigger_count = 0

    for index, item in enumerate(evals):
        prefix = f"evals[{index}]"
        require(isinstance(item, dict), f"{prefix}: must be an object", errors)
        if not isinstance(item, dict):
            continue

        eval_id = item.get("id")
        require(isinstance(eval_id, str) and bool(eval_id.strip()), f"{prefix}: id must be non-empty text", errors)
        if isinstance(eval_id, str):
            if eval_id in seen_ids:
                errors.append(f"{prefix}: duplicate id {eval_id!r}")
            seen_ids.add(eval_id)
        else:
            eval_id = prefix

        require(isinstance(item.get("prompt"), str) and bool(item["prompt"].strip()), f"{eval_id}: prompt must be non-empty text", errors)
        require(isinstance(item.get("expected_output"), str) and bool(item["expected_output"].strip()), f"{eval_id}: expected_output must be non-empty text", errors)

        trigger_expected = item.get("trigger_expected")
        require(isinstance(trigger_expected, bool), f"{eval_id}: trigger_expected must be boolean", errors)
        if trigger_expected is True:
            trigger_count += 1
        elif trigger_expected is False:
            non_trigger_count += 1

        files = item.get("files")
        require(isinstance(files, list), f"{eval_id}: files must be a list", errors)
        if isinstance(files, list):
            for file_index, file_item in enumerate(files):
                require(isinstance(file_item, str), f"{eval_id}.files[{file_index}]: must be text", errors)

        assertions = item.get("assertions")
        require(isinstance(assertions, list) and bool(assertions), f"{eval_id}: assertions must be a non-empty list", errors)
        if isinstance(assertions, list):
            for assertion_index, assertion in enumerate(assertions):
                validate_assertion(assertion, str(eval_id), assertion_index, errors)

    require(trigger_count > 0, "At least one should-trigger eval is required", errors)
    require(non_trigger_count > 0, "At least one should-not-trigger eval is required", errors)

    return not errors, errors


def load_results(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"Invalid results JSON: {exc}"]

    if isinstance(data, dict) and isinstance(data.get("results"), list):
        result_items = data["results"]
    elif isinstance(data, list):
        result_items = data
    else:
        return None, ["Results must be a list or an object with a results list"]

    results = {}
    errors = []
    for index, item in enumerate(result_items):
        if not isinstance(item, dict):
            errors.append(f"results[{index}]: must be an object")
            continue
        result_id = item.get("id")
        if not isinstance(result_id, str) or not result_id.strip():
            errors.append(f"results[{index}]: id must be non-empty text")
            continue
        if result_id in results:
            errors.append(f"results[{index}]: duplicate id {result_id!r}")
            continue
        results[result_id] = item

    return results, errors


def result_exit_code(result, command):
    exit_codes = result.get("exit_codes")
    if isinstance(exit_codes, dict) and command in exit_codes:
        return exit_codes[command]

    commands = result.get("commands")
    if isinstance(commands, list):
        for item in commands:
            if isinstance(item, dict) and item.get("command") == command:
                return item.get("exit_code")

    return None


def result_files(result):
    files = result.get("files", [])
    if not isinstance(files, list):
        return set()
    return {item for item in files if isinstance(item, str)}


def run_assertions(evals_path, results_path, workspace=None):
    valid, errors = validate_evals(evals_path)
    if not valid:
        return False, errors

    data = json.loads(Path(evals_path).read_text(encoding="utf-8"))
    results, result_errors = load_results(results_path)
    if result_errors:
        return False, result_errors

    errors = []
    workspace_path = Path(workspace).resolve() if workspace else None

    for item in data["evals"]:
        eval_id = item["id"]
        result = results.get(eval_id)
        if not result:
            errors.append(f"{eval_id}: missing result")
            continue

        output = result.get("output", "")
        if not isinstance(output, str):
            errors.append(f"{eval_id}: result output must be text")
            output = ""

        produced_files = result_files(result)
        for assertion in item["assertions"]:
            assertion_type = assertion["type"]
            if assertion_type == "contains":
                value = assertion["value"]
                if value not in output:
                    errors.append(f"{eval_id}: output does not contain {value!r}")
            elif assertion_type == "not_contains":
                value = assertion["value"]
                if value in output:
                    errors.append(f"{eval_id}: output unexpectedly contains {value!r}")
            elif assertion_type == "file_exists":
                path = assertion["path"]
                exists_in_result = path in produced_files
                exists_in_workspace = bool(workspace_path and (workspace_path / path).exists())
                if not exists_in_result and not exists_in_workspace:
                    errors.append(f"{eval_id}: file does not exist: {path}")
            elif assertion_type == "exit_code":
                command = assertion["command"]
                expected = assertion["value"]
                actual = result_exit_code(result, command)
                if actual != expected:
                    errors.append(f"{eval_id}: exit code for {command!r} was {actual!r}, expected {expected}")

    return not errors, errors


def main():
    parser = argparse.ArgumentParser(description="Validate eval JSON structure and assertions.")
    parser.add_argument("evals_json", help="Path to evals/evals.json")
    parser.add_argument(
        "--results",
        help="Optional result JSON. When provided, execute assertions against result outputs.",
    )
    parser.add_argument(
        "--workspace",
        help="Optional workspace root for file_exists assertions.",
    )
    args = parser.parse_args()

    if args.results:
        valid, errors = run_assertions(args.evals_json, args.results, args.workspace)
        success_message = "Eval assertions passed!"
    else:
        valid, errors = validate_evals(args.evals_json)
        success_message = "Eval definitions are valid!"

    if valid:
        print(success_message)
        sys.exit(0)

    for error in errors:
        print(f"[ERROR] {error}")
    sys.exit(1)


if __name__ == "__main__":
    main()
