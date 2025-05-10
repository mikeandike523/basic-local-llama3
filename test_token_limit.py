#!/usr/bin/env python3
"""
Script to probe a Flask Llama3 API server for its maximum token handling capacity.
This client will send progressively larger user messages until the API returns an error,
logging at which point the limit appears to be exceeded.
"""
import argparse
import requests
import time
import sys


def generate_content(token_count: int) -> str:
    """Generate a dummy message roughly token_count tokens long."""
    # Using a single repeated word with spaces approximates token count.
    return ("token " * token_count).strip()


def test_token_limits(
    host: str,
    port: int,
    start: int,
    step: int,
    max_tokens: int,
    timeout: int
) -> None:
    url = f"http://{host}:{port}/completion"
    print(f"Testing token limits against {url}")

    for count in range(start, max_tokens + 1, step):
        content = generate_content(count)
        payload = {
            "messages": [{"role": "user", "content": content}],
            "max_tokens": None  # rely on server defaults for response length
        }
        try:
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=timeout)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                gen = data.get("result", {}).get("content", "<no content>")
                print(
                    f"OK  @ tokens={count:6d} | resp_len={len(gen):5d} | time={elapsed:0.2f}s"
                )
            else:
                print(
                    f"ERROR @ tokens={count:6d} | status={response.status_code} | "
                    f"body={response.text[:200]}"
                )
                print("Stopping test; token limit likely reached.")
                break

        except requests.exceptions.RequestException as e:
            print(f"EXCEPTION @ tokens={count:6d} | {e}")
            print("Stopping test due to exception.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Test Flask Llama3 API token limits by sending incremental payloads."
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="API server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000,
        help="API server port (default: 5000)"
    )
    parser.add_argument(
        "--start", type=int, default=1000,
        help="Starting token count (default: 1000)"
    )
    parser.add_argument(
        "--step", type=int, default=1000,
        help="Increment step for token count (default: 1000)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=20000,
        help="Maximum token count to test (default: 20000)"
    )
    parser.add_argument(
        "--timeout", type=int, default=60,
        help="Request timeout in seconds (default: 60)"
    )

    args = parser.parse_args()

    test_token_limits(
        host=args.host,
        port=args.port,
        start=args.start,
        step=args.step,
        max_tokens=args.max_tokens,
        timeout=args.timeout
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Interrupted by user")
