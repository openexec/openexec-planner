"""OpenExec Orchestration CLI entrypoint."""

import argparse
import json
import os
import sys
from pathlib import Path

from .parser import IntentParser
from .generator import StoryGenerator
from .llm_generator import LLMStoryGenerator
from .goal_tree import GoalTreeBuilder
from .scheduler import Scheduler
from .utils import safe_resolve_path


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        prog="openexec-orchestration",
        description="OpenExec Orchestration - AI Planning Engine",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # parse command
    parse_parser = subparsers.add_parser("parse", help="Parse an intent document")
    parse_parser.add_argument("file", type=Path, help="Path to intent document")
    parse_parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate stories from intent")
    gen_parser.add_argument("file", type=Path, help="Path to intent document")
    gen_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: stdout)",
    )
    gen_parser.add_argument(
        "--model",
        "-m",
        default="sonnet",
        help="Model to use for generation (opus, sonnet, haiku, gpt-5, gemini-3.1-pro-preview)",
    )
    gen_parser.add_argument(
        "--reviewer",
        "-r",
        help="Model to use for reviewing generated stories (enables review step)",
    )

    # build-tree command
    tree_parser = subparsers.add_parser("build-tree", help="Build goal tree from intent")
    tree_parser.add_argument("file", type=Path, help="Path to intent document")
    tree_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: stdout)",
    )

    # schedule command
    sched_parser = subparsers.add_parser("schedule", help="Generate execution schedule")
    sched_parser.add_argument("file", type=Path, help="Path to intent or stories file")
    sched_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: stdout)",
    )

    # version command
    subparsers.add_parser("version", help="Show version")

    # wizard command
    wizard_parser = subparsers.add_parser("wizard", help="Interactive intent gathering")
    wizard_parser.add_argument("--message", "-m", help="User message")
    wizard_parser.add_argument("--state", "-s", help="Current state as JSON string")
    wizard_parser.add_argument("--state-file", type=Path, help="Path to state JSON file")
    wizard_parser.add_argument("--model", default="sonnet", help="Model to use")
    wizard_parser.add_argument("--render", action="store_true", help="Render current state to INTENT.md")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "version":
        from . import __version__
        print(f"openexec-orchestration {__version__}")
        return 0

    if args.command == "parse":
        return cmd_parse(args)

    if args.command == "generate":
        return cmd_generate(args)

    if args.command == "build-tree":
        return cmd_build_tree(args)

    if args.command == "schedule":
        return cmd_schedule(args)

    if args.command == "wizard":
        return cmd_wizard(args)

    return 0


def cmd_wizard(args: argparse.Namespace) -> int:
    """Handle wizard command."""
    from .wizard import IntentWizard, IntentState
    
    wizard = IntentWizard(model=args.model)
    
    # Load state
    if args.state:
        wizard.state = IntentState.model_validate_json(args.state)
    elif args.state_file and args.state_file.exists():
        wizard.state = IntentState.model_validate_json(args.state_file.read_text())
        
    if args.render:
        print(wizard.render_intent_md())
        return 0
        
    if not args.message:
        print("Error: --message required for wizard interaction", file=sys.stderr)
        return 1
        
    result = wizard.process_message(args.message)
    
    # If a state file was provided, update it
    if args.state_file:
        args.state_file.write_text(wizard.state.model_dump_json(indent=2))
        
    print(result.model_dump_json(indent=2))
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    """Handle parse command."""
    # Security: Prevent path traversal
    try:
        safe_path = safe_resolve_path(os.getcwd(), args.file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not safe_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    parser = IntentParser()
    result = parser.parse(safe_path, base_dir=os.getcwd())

    if args.format == "json":
        # Remove raw_content for cleaner output
        output = {k: v for k, v in result.items() if k != "raw_content"}
        print(json.dumps(output, indent=2))
    else:
        print(f"Title: {result['title']}")
        print()
        print("Goals:")
        for goal in result["goals"]:
            print(f"  - {goal}")
        print()
        print("Requirements:")
        for req in result["requirements"]:
            print(f"  - {req}")
        print()
        print("Constraints:")
        for constraint in result["constraints"]:
            print(f"  - {constraint}")

    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle generate command."""
    # Security: Prevent path traversal
    try:
        safe_path = safe_resolve_path(os.getcwd(), args.file)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not safe_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    model = getattr(args, "model", "sonnet")
    reviewer = getattr(args, "reviewer", None)

    # Detect CLI availability
    import shutil
    cli_commands = {"opus": "claude", "sonnet": "claude", "haiku": "claude",
                    "gpt-5": "codex", "gpt-5-codex": "codex",
                    "gemini-3.1-pro-preview": "gemini", "gemini-3.1-flash-preview": "gemini"}
    executor_cli = cli_commands.get(model, "claude")
    executor_cli_available = shutil.which(executor_cli) is not None

    print(f"Executor model: {model} (CLI: {executor_cli})")
    if executor_cli_available:
        print(f"  Using CLI mode: {executor_cli}")
    else:
        print(f"  CLI '{executor_cli}' not found, will try API")

    if reviewer:
        reviewer_cli = cli_commands.get(reviewer, "claude")
        reviewer_cli_available = shutil.which(reviewer_cli) is not None
        print(f"Reviewer model: {reviewer} (CLI: {reviewer_cli})")
        if reviewer_cli_available:
            print(f"  Using CLI mode: {reviewer_cli}")
        else:
            print(f"  CLI '{reviewer_cli}' not found, will try API")

    # Read raw intent content
    intent_content = safe_path.read_text()

    # Use LLM-based generator for better quality stories
    try:
        generator = LLMStoryGenerator(model=model)
        print("Generating stories and goals...")
        result_data = generator.generate(intent_content)
        stories_count = len(result_data.get("stories", []))
        print(f"Generated {stories_count} stories")

        # Review step if reviewer is specified
        if reviewer:
            print("Reviewing stories...")
            result_data = generator.review(result_data, intent_content, reviewer_model=reviewer)
            print("Review complete")

    except ImportError as e:
        print(f"Warning: LLM packages not installed ({e})", file=sys.stderr)
        print("Install with: pip install anthropic openai google-generativeai", file=sys.stderr)
        print("Falling back to rule-based generation...", file=sys.stderr)
        parser = IntentParser()
        intent = parser.parse(safe_path, base_dir=os.getcwd())
        fallback_generator = StoryGenerator()
        result_data = {"schema_version": "1.0", "goals": [], "stories": fallback_generator.generate(intent)}
    except ValueError as e:
        # JSON parsing errors or API key errors
        error_msg = str(e)
        if "API_KEY" in error_msg.upper():
            print(f"Warning: API key not set - {error_msg}", file=sys.stderr)
        else:
            print(f"Warning: LLM response parsing failed", file=sys.stderr)
            print(f"Error: {error_msg[:500]}", file=sys.stderr)
        print("Falling back to rule-based generation...", file=sys.stderr)
        parser = IntentParser()
        intent = parser.parse(safe_path, base_dir=os.getcwd())
        fallback_generator = StoryGenerator()
        result_data = {"schema_version": "1.0", "goals": [], "stories": fallback_generator.generate(intent)}
    except KeyError as e:
        # This shouldn't happen - indicates a bug in response handling
        import traceback
        print(f"Warning: Unexpected KeyError in LLM generation: {e}", file=sys.stderr)
        print("This may indicate the CLI returned unexpected output format.", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        print("Falling back to rule-based generation...", file=sys.stderr)
        parser = IntentParser()
        intent = parser.parse(safe_path, base_dir=os.getcwd())
        fallback_generator = StoryGenerator()
        result_data = {"schema_version": "1.0", "goals": [], "stories": fallback_generator.generate(intent)}
    except Exception as e:
        import traceback
        print(f"Warning: LLM generation failed ({type(e).__name__}: {e})", file=sys.stderr)
        print("Falling back to rule-based generation...", file=sys.stderr)
        parser = IntentParser()
        intent = parser.parse(safe_path, base_dir=os.getcwd())
        fallback_generator = StoryGenerator()
        result_data = {"schema_version": "1.0", "goals": [], "stories": fallback_generator.generate(intent)}

    output = json.dumps(result_data, indent=2)
    if args.output:
        args.output.write_text(output)
        print(f"Stories written to {args.output}")
    else:
        print(output)

    return 0


def cmd_build_tree(args: argparse.Namespace) -> int:
    """Handle build-tree command."""
    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    parser = IntentParser()
    intent = parser.parse(args.file)

    builder = GoalTreeBuilder()
    tree = builder.build(intent)

    output = json.dumps(tree, indent=2)
    if args.output:
        args.output.write_text(output)
        print(f"Goal tree written to {args.output}")
    else:
        print(output)

    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    """Handle schedule command."""
    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    # Check if file is JSON (stories) or markdown (intent)
    if args.file.suffix == ".json":
        data = json.loads(args.file.read_text())
    else:
        parser = IntentParser()
        intent = parser.parse(args.file)
        generator = StoryGenerator()
        data = generator.generate(intent)

    scheduler = Scheduler()
    schedule = scheduler.schedule(data)

    output = json.dumps(schedule, indent=2)
    if args.output:
        args.output.write_text(output)
        print(f"Schedule written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
