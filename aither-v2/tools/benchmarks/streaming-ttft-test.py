#!/usr/bin/env python3
"""Streaming TTFT measurement tool.

Measures Time To First Token (TTFT) via SSE streaming for OpenAI-compatible endpoints.
Usage:
    python3 streaming-ttft-test.py \\
        --target 14b \\
        --url http://vllm-14b-instruct.aither-inference.svc:8000/v1/chat/completions \\
        --model qwen-14b \\
        --api-key $VLLM_API_KEY \\
        --output /tmp/ttft-results.jsonl
"""
import argparse
import json
import sys
import time
import urllib.request

def stream_ttft(url: str, model: str, api_key: str, prompt: str, max_tokens: int = 64):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}] if "/chat/" in url else [],
        "prompt": prompt if "/completions" in url and "/chat/" not in url else None,
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0,
    }
    # Clean None
    payload = {k: v for k, v in payload.items() if v is not None}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    data = json.dumps(payload).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    ttft = None
    total_start = time.time()
    first_chunk_time = None
    chunk_count = 0
    total_text = ""

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    chunk = line[6:]
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        ttft = first_chunk_time - total_start
                    if chunk == "[DONE]":
                        break
                    chunk_count += 1
                    try:
                        d = json.loads(chunk)
                        if "choices" in d and d["choices"]:
                            delta = d["choices"][0].get("delta", {})
                            text = delta.get("content", "")
                            total_text += text
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        return {"error": str(e), "ttft": None}

    total_time = time.time() - total_start
    token_count = len(total_text.split())
    tokens_per_sec = token_count / total_time if total_time > 0 else 0

    return {
        "ttft": round(ttft, 4) if ttft else None,
        "total_time": round(total_time, 4),
        "chunk_count": chunk_count,
        "approx_tokens": token_count,
        "tokens_per_sec": round(tokens_per_sec, 2),
        "text_preview": total_text[:100],
    }


def main():
    parser = argparse.ArgumentParser(description="Streaming TTFT test")
    parser.add_argument("--target", required=True, help="Model target name (14b, 32b)")
    parser.add_argument("--url", required=True, help="Full URL to endpoint")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--api-key", required=True, help="API key")
    parser.add_argument("--prompt", default="What is the capital of France?",
                        help="Test prompt")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--output", help="Output JSONL file")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs")
    args = parser.parse_args()

    results = []
    for i in range(1, args.runs + 1):
        # Warm prompt first, then test
        prompt = args.prompt if i > 1 else args.prompt
        print(f"Run {i}/{args.runs}...", file=sys.stderr)
        res = stream_ttft(args.url, args.model, args.api_key, prompt, args.max_tokens)
        res["run"] = i
        res["target"] = args.target
        res["url"] = args.url
        res["model"] = args.model
        results.append(res)
        print(json.dumps(res, ensure_ascii=False), file=sys.stderr if not args.output else sys.stdout)
        time.sleep(2)

    if args.output:
        with open(args.output, 'w') as f:
            for r in results:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        print(f"Results saved to {args.output}", file=sys.stderr)

    # Summary
    ttft_vals = [r["ttft"] for r in results if r.get("ttft")]
    total_vals = [r["total_time"] for r in results if r.get("total_time")]
    tps_vals = [r["tokens_per_sec"] for r in results if r.get("tokens_per_sec")]

    if ttft_vals:
        print(f"\n=== Summary for {args.target} ===")
        print(f"  TTFT (avg): {sum(ttft_vals)/len(ttft_vals):.4f}s")
        print(f"  TTFT (min): {min(ttft_vals):.4f}s")
        print(f"  TTFT (max): {max(ttft_vals):.4f}s")
        print(f"  Total (avg): {sum(total_vals)/len(total_vals):.4f}s")
        print(f"  Tokens/sec (avg): {sum(tps_vals)/len(tps_vals):.2f}")


if __name__ == "__main__":
    main()
