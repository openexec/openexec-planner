"""OpenExec Orchestration CLI entrypoint."""

import argparse
import json
import sys
from pathlib import Path

from .parser import IntentParser
from .generator import StoryGenerator
from .goal_tree import GoalTreeBuilder
from .scheduler import Scheduler


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

    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    """Handle parse command."""
    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    parser = IntentParser()
    result = parser.parse(args.file)

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
    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    parser = IntentParser()
    intent = parser.parse(args.file)

    generator = StoryGenerator()
    stories = generator.generate(intent)

    output = json.dumps(stories, indent=2)
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
