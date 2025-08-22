import os
import glob
import json
from typing import Dict, Any, List, Tuple

try:
    import orjson as jsonlib

    def dumps(o):
        return jsonlib.dumps(o).decode("utf-8")
except Exception:
    import json as jsonlib  # type: ignore

    def dumps(o):
        return jsonlib.dumps(o, ensure_ascii=False)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from llmlingua import PromptCompressor


console = Console()


def load_json_prompts(paths: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    items = []
    for p in paths:
        for f in glob.glob(p):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                items.append((f, data))
            except Exception as e:
                console.print(f"[yellow]Warn:[/] failed to read {f}: {e}\n")
    return items


def collect_system_prompts(obj: Any) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []

    def walk(prefix: str, node: Any):
        if isinstance(node, dict):
            for k, v in node.items():
                key_path = f"{prefix}.{k}" if prefix else str(k)
                if k == "system_prompt" and isinstance(v, str):
                    found.append((key_path, v))
                else:
                    walk(key_path, v)
        elif isinstance(node, list):
            for idx, v in enumerate(node):
                walk(f"{prefix}[{idx}]", v)
    walk("", obj)
    return found


def main():
    model_name = os.getenv(
        "LLMLINGUA_MODEL", "microsoft/llmlingua-2-xlm-roberta-large-meetingbank")
    use_llmlingua2 = os.getenv(
        "LLMLINGUA2", "true").lower() in ("1", "true", "yes")
    rate_env = os.getenv("LLMLINGUA_RATE", "0.5")
    try:
        rate = float(rate_env)
    except Exception:
        rate = 0.5

    compressor = PromptCompressor(
        model_name=model_name, use_llmlingua2=use_llmlingua2)

    base_dir = os.path.dirname(os.path.dirname(__file__))
    paths = [
        os.path.join(base_dir, "config", "prompts_summarize", "*.json"),
        os.path.join(base_dir, "config", "prompts_judge", "*.json"),
    ]

    datasets = load_json_prompts(paths)
    console.rule("LLMLingua Prompt Compression Test")
    console.print(
        f"Model: [bold]{model_name}[/], LLMLingua2: [bold]{use_llmlingua2}[/], rate: [bold]{rate}[/]")

    for file_path, data in datasets:
        console.rule(f"File: {file_path}")
        sys_prompts = collect_system_prompts(data)
        if not sys_prompts:
            console.print("[yellow]No system_prompt fields found[/]")
            continue

        for key_path, system_prompt in sys_prompts:
            console.print(
                Panel.fit(f"Key: [bold]{key_path}[/]", title="System Prompt Field"))

            try:
                # Use rate compression with visualization of dropped tokens
                result = compressor.compress_prompt(
                    system_prompt,
                    rate=rate,
                    return_vis=True,
                )
            except TypeError:
                # Fallback to token target if rate not supported by installed version
                est_tokens = max(64, int(len(system_prompt) / 4))
                result = compressor.compress_prompt(
                    system_prompt,
                    target_token=est_tokens,
                    return_vis=True,
                )

            compressed = result.get("compressed_prompt", "")
            origin_tokens = result.get("origin_tokens")
            compressed_tokens = result.get("compressed_tokens")
            ratio = result.get("ratio")
            vis = result.get("vis") or result.get("visualization") or {}

            # Summary table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Metric")
            table.add_column("Value")
            table.add_row("Origin tokens", str(origin_tokens))
            table.add_row("Compressed tokens", str(compressed_tokens))
            table.add_row("Compression ratio", f"{ratio}")
            console.print(table)

            # Original and compressed prompt blocks
            console.print(Panel(Markdown(
                f"## Original\n\n````\n{system_prompt}\n````"), title="Original Prompt", expand=False))
            console.print(Panel(Markdown(
                f"## Compressed\n\n````\n{compressed}\n````"), title="Compressed Prompt", expand=False))

            # Visualization: highlight dropped tokens/segments when provided
            if vis:
                console.print(Panel(Markdown(
                    f"## Dropped Tokens Visualization\n\n````json\n{dumps(vis)}\n````"), title="LLMLingua Visualization", expand=False))
            console.print()


if __name__ == "__main__":
    main()
