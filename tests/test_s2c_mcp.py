"""The optional local MCP adapter completes a real stdio handshake."""

from pathlib import Path
import os
import sys
import unittest

try:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
except ImportError:
    ClientSession = None


SERVER = Path(__file__).resolve().parents[1] / "skills/scan-to-comprehend/integrations/mcp_server.py"


@unittest.skipUnless(ClientSession is not None and os.environ.get("S2C_TEST_MCP") == "1",
                     "optional MCP handshake requires S2C_TEST_MCP=1 and the MCP SDK")
class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_lists_both_audit_tools(self):
        server = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                self.assertEqual(names, {"audit_public_url", "audit_html_prototype"})


if __name__ == "__main__":
    unittest.main()
