from __future__ import annotations

"""
Minimal MCP server exposing Momentum actions as tools.
This is a basic, stateless implementation for local development/testing.
"""

from typing import Any, Dict

try:
    from mcp.server.fastmcp import FastMCP, Context
except Exception:  # Allow running without MCP installed
    FastMCP = None  # type: ignore
    Context = Any  # type: ignore

from .momentum_client import create_momentum_client


def build_mcp_app():
    if FastMCP is None:
        raise RuntimeError("mcp is not installed. Please install 'mcp'.")
    momentum = create_momentum_client()
    mcp = FastMCP("momentum-tools")

    @mcp.tool()
    def momentum_status(ctx: Context) -> Dict[str, Any]:  # type: ignore
        return momentum.get_status()

    @mcp.tool()
    def momentum_start(ctx: Context) -> str:  # type: ignore
        momentum.start()
        return "started"

    @mcp.tool()
    def momentum_simulate(ctx: Context) -> str:  # type: ignore
        momentum.simulate()
        return "simulate-started"

    @mcp.tool()
    def momentum_stop(ctx: Context) -> str:  # type: ignore
        momentum.stop()
        return "stopped"

    @mcp.tool()
    def momentum_devices(ctx: Context) -> Any:  # type: ignore
        return momentum.get_devices()

    @mcp.tool()
    def momentum_version(ctx: Context) -> Any:  # type: ignore
        return momentum.get_version()

    @mcp.tool()
    def momentum_status_or_version(ctx: Context) -> Any:  # type: ignore
        return {"status": momentum.get_status(), "version": momentum.get_version()}

    @mcp.tool()
    def momentum_nests(ctx: Context) -> Any:  # type: ignore
        return momentum.get_nests()

    @mcp.tool()
    def momentum_processes(ctx: Context) -> Any:  # type: ignore
        return momentum.get_processes()

    @mcp.tool()
    def momentum_workqueue(ctx: Context) -> Any:  # type: ignore
        return momentum.get_workqueue()

    @mcp.tool()
    def momentum_run_process(
        ctx: Context,
        process: str,
        variables: Dict[str, Any] | None = None,
        iterations: int = 1,
        append: bool = True,
        minimum_delay: int = 0,
        workunit_name: str | None = None,
    ) -> Any:  # type: ignore
        return momentum.run_process(
            process=process,
            variables=variables or {},
            iterations=iterations,
            append=append,
            minimum_delay=minimum_delay,
            workunit_name=workunit_name,
        )

    return mcp


def main():  # pragma: no cover
    mcp = build_mcp_app()
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()


