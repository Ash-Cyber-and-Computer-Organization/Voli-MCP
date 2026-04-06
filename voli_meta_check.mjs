import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const ENDPOINT = "https://voli-mcp-production.up.railway.app/sse";

async function main() {
    const transport = new SSEClientTransport(new URL(ENDPOINT));
    const client = new Client({ name: "voli-meta-check", version: "1.0.0" });
    await client.connect(transport);

    const resp = await client.listTools();
    const tools = resp.tools || [];
    console.log("Raw tool keys from wire response:");
    for (const t of tools) {
        console.log("  All keys:", JSON.stringify(Object.keys(t)));
        console.log("  tool._meta:", JSON.stringify(t._meta));
        console.log("  tool.meta:", JSON.stringify(t.meta));
        // Dump full tool
        console.log("  Full tool JSON:", JSON.stringify(t, null, 2).slice(0, 500));
    }

    await client.close();
}

main().catch(err => { console.error(err); process.exit(1); });
