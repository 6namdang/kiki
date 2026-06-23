import argparse

from kiki.config import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_TRANSPORT
from kiki.server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="kiki", description="Biological sequence MCP server")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the MCP server")
    serve.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=DEFAULT_TRANSPORT,
        help="MCP transport (default: http)",
    )
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    args = parser.parse_args()

    if args.command == "serve":
        mcp = create_server()
        if args.transport == "http":
            mcp.run(transport="http", host=args.host, port=args.port)
        else:
            mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
