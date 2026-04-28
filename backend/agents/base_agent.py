"""
Base agent class. All agents inherit from this.
Each agent registers tools (async functions) and can call them by name.
"""
from typing import Any, Callable, Dict, List, Optional
import asyncio


class Tool:
    def __init__(self, name: str, fn: Callable, description: str):
        self.name = name
        self.fn = fn
        self.description = description

    async def run(self, **kwargs) -> Any:
        if asyncio.iscoroutinefunction(self.fn):
            return await self.fn(**kwargs)
        return self.fn(**kwargs)


class BaseAgent:
    name: str = "base"
    description: str = ""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self.register_tools()

    def register_tools(self):
        """Override in subclass to register tools."""
        pass

    def tool(self, name: str, description: str = ""):
        """Decorator to register a method as a tool."""
        def decorator(fn: Callable):
            self._tools[name] = Tool(name=name, fn=fn, description=description)
            return fn
        return decorator

    def _register(self, name: str, fn: Callable, description: str = ""):
        self._tools[name] = Tool(name=name, fn=fn, description=description)

    async def run_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in agent '{self.name}'")
        return await self._tools[tool_name].run(**kwargs)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclass to handle a task."""
        raise NotImplementedError
