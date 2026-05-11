"""
CLI Interface — Component 6
=============================
Command-line interface for the Multi-Agent Research & Analysis System.

USAGE MODES:
    1. Direct mode:
       python main.py "What are AI trends?"
       python main.py "Analyze sales" --data sales.csv --output report.md

    2. Interactive mode:
       python main.py --interactive

    3. Quiet mode (pipe-friendly):
       python main.py "query" --quiet > report.md

EXAMPLES:
    python main.py "Latest trends in renewable energy"
    python main.py "Analyze this dataset" -d data/uploads/sales.csv -o reports/sales.md
    python main.py -i
    python main.py "Query" --data file.csv --output out.md --model mixtral-8x7b-32768
"""

import argparse
import sys
import os
import time
from pathlib import Path

from loguru import logger
from dotenv import load_dotenv

# Load environment before anything else
load_dotenv()

# Add project root to path for proper imports
sys.path.insert(0, str(Path(__file__).parent))


# ── Styling helpers ───────────────────────────────────────────────────────────

COLORS = {
    "cyan": "\033[96m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

def colorize(text: str, *styles: str) -> str:
    """Apply ANSI color codes (safe on Windows with Windows Terminal)."""
    codes = "".join(COLORS.get(s, "") for s in styles)
    return f"{codes}{text}{COLORS['reset']}"

def print_banner():
    """Print the system banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║         🤖  MULTI-AGENT AI RESEARCH SYSTEM  🤖              ║
║         Powered by LangGraph + Groq (Llama 3)               ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(colorize(banner, "cyan", "bold"))

def print_section(title: str):
    """Print a section divider."""
    print(f"\n{colorize('─' * 60, 'dim')}")
    print(colorize(f"  {title}", "yellow", "bold"))
    print(f"{colorize('─' * 60, 'dim')}\n")

def print_stats(result: dict, elapsed: float):
    """Print execution statistics."""
    print_section("📊 Execution Statistics")
    print(f"  ⏱  Total time:   {colorize(f'{elapsed:.1f}s', 'cyan')}")
    print(f"  🔄 Iterations:   {colorize(str(result.get('iterations', 0)), 'cyan')}")
    print(f"  📰 Sources:      {colorize(str(len(result.get('search_results', []))), 'cyan')}")
    print(f"  📂 Data used:    {colorize('Yes' if result.get('data_summary') else 'No', 'cyan')}")

    errors = result.get("errors", [])
    if errors:
        print(f"\n  {colorize(f'⚠️  {len(errors)} error(s) logged:', 'yellow')}")
        for err in errors:
            print(f"     • {colorize(err[:80], 'red')}")
    else:
        print(f"\n  {colorize('✅ No errors', 'green')}")


# ── Interactive mode ──────────────────────────────────────────────────────────

def run_interactive():
    """
    Run in interactive prompt mode.
    Guides the user through entering query, data file, and output file.
    """
    print_banner()
    print_section("🎯 Interactive Mode")

    # Collect inputs
    print(colorize("Enter your research query:", "bold"))
    query = input("  → ").strip()

    if not query:
        print(colorize("❌ Query cannot be empty.", "red"))
        sys.exit(1)

    print(colorize("\nData file path (CSV/Excel) [optional, press Enter to skip]:", "bold"))
    data_path_input = input("  → ").strip() or None

    if data_path_input and not os.path.exists(data_path_input):
        print(colorize(f"⚠️  Warning: File '{data_path_input}' not found — will skip data analysis.", "yellow"))
        data_path_input = None

    print(colorize("\nOutput file path [optional, press Enter to print only]:", "bold"))
    output_path = input("  → ").strip() or None

    # Run workflow
    _execute_workflow(query, data_path_input, output_path, quiet=False)


# ── Core execution ────────────────────────────────────────────────────────────

def _execute_workflow(
    query: str,
    data_path: str = None,
    output_path: str = None,
    quiet: bool = False,
):
    """
    Core execution function shared by all modes.

    Args:
        query: Research question
        data_path: Optional CSV/Excel file path
        output_path: Optional file path to save report
        quiet: If True, only prints the report (no banners/stats)
    """
    if not quiet:
        print_section("🚀 Starting Workflow")
        print(f"  Query:  {colorize(query[:80], 'cyan')}")
        if data_path:
            print(f"  Data:   {colorize(data_path, 'cyan')}")
        print()

    # Lazy import to allow faster --help and error messages
    try:
        from src.graph.workflow import ResearchWorkflow
    except ImportError as e:
        print(colorize(f"❌ Import error: {e}", "red"))
        print(colorize("   Make sure all dependencies are installed: pip install -r requirements.txt", "yellow"))
        sys.exit(1)

    start_time = time.time()

    try:
        workflow = ResearchWorkflow()
        result = workflow.run(query, data_path)
    except Exception as e:
        print(colorize(f"\n❌ Workflow failed: {e}", "red"))
        logger.exception("Workflow execution failed")
        sys.exit(1)

    elapsed = time.time() - start_time
    final_report = result.get("final_report", "*No report generated.*")

    # ── Print report ──────────────────────────────────────────────────────────
    if not quiet:
        print_section("📄 Final Report")

    print(final_report)

    if not quiet:
        print_stats(result, elapsed)

    # ── Save to file ──────────────────────────────────────────────────────────
    if output_path:
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_report)

            if not quiet:
                print(f"\n  {colorize(f'💾 Report saved to: {output_path}', 'green')}")

        except Exception as e:
            print(colorize(f"⚠️  Could not save to '{output_path}': {e}", "yellow"))


# ── Argument Parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI argument parser.

    Design decision: nargs="*" for query allows:
    - python main.py "single query"
    - python main.py What are AI trends  (no quotes needed)
    """
    parser = argparse.ArgumentParser(
        prog="agentic-ai",
        description=(
            "Multi-Agent AI Research & Analysis System\n"
            "Uses LangGraph + Groq (Llama 3) to research and analyze topics."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "What are AI trends in healthcare?"
  python main.py "Analyze this sales data" --data sales.csv
  python main.py "Research and analyze" --data data.csv --output report.md
  python main.py --interactive
  python main.py "Query" --quiet > report.md
        """,
    )

    parser.add_argument(
        "query",
        nargs="*",
        help="Research query or analysis task (wrap in quotes for multi-word queries)",
    )
    parser.add_argument(
        "-d", "--data",
        metavar="FILE",
        help="Path to CSV or Excel data file for analysis",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Save final report to this file (markdown format)",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive prompt mode",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress banners and stats — print only the report (pipe-friendly)",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Skip the banner but show stats",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


# ── Main entry point ──────────────────────────────────────────────────────────

def main():
    """
    Main CLI entry point.

    Handles three modes:
    1. Interactive mode (--interactive)
    2. Direct mode (query as positional args)
    3. Help (no args)
    """
    parser = build_parser()
    args = parser.parse_args()

    # Configure loguru: suppress verbose logs in non-debug mode
    logger.remove()
    if not args.quiet:
        logger.add(sys.stderr, level="INFO", format="<dim>{time:HH:mm:ss}</dim> | {level} | {message}")
    else:
        logger.add(sys.stderr, level="ERROR")

    # ── Interactive mode ──────────────────────────────────────────────────────
    if args.interactive:
        run_interactive()
        return

    # ── Direct mode ───────────────────────────────────────────────────────────
    if not args.query:
        parser.print_help()
        print(colorize("\n💡 Tip: Use -i for interactive mode, or provide a query.", "yellow"))
        sys.exit(0)

    query = " ".join(args.query)

    if not query.strip():
        print(colorize("❌ Query cannot be empty.", "red"))
        sys.exit(1)

    # Validate data file if provided
    if args.data and not os.path.exists(args.data):
        print(colorize(f"⚠️  Warning: Data file '{args.data}' not found.", "yellow"))
        print(colorize("   Proceeding with research-only mode.", "yellow"))
        args.data = None

    # Print banner unless quiet
    if not args.quiet and not args.no_banner:
        print_banner()

    # Execute
    _execute_workflow(
        query=query,
        data_path=args.data,
        output_path=args.output,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
