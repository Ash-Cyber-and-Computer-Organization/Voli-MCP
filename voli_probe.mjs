import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

const ENDPOINT = "https://voli-mcp-production.up.railway.app/sse";

async function main() {
    console.log("=== VOLI-MCP ENDPOINT PROBE ===\n");
    console.log(`Connecting to: ${ENDPOINT}`);

    const transport = new SSEClientTransport(new URL(ENDPOINT));
    const client = new Client({ name: "voli-qa-probe", version: "1.0.0" });

    try {
        await client.connect(transport);
        console.log("✅ Connected successfully\n");
    } catch (err) {
        console.error("❌ Connection failed:", err.message);
        process.exit(1);
    }

    // LIST TOOLS
    let tools = [];
    try {
        const resp = await client.listTools();
        tools = resp.tools || [];
        console.log(`Found ${tools.length} tools:\n`);
    } catch (err) {
        console.error("❌ listTools failed:", err.message);
        process.exit(1);
    }

    // SCHEMA AUDIT + PRINT TOOL DETAILS
    const auditResults = [];

    for (const tool of tools) {
        const audit = {
            name: tool.name,
            hasDescription: !!tool.description,
            inputSchemaTyped: !!(tool.inputSchema && tool.inputSchema.type),
            inputHasProperties: !!(tool.inputSchema && tool.inputSchema.properties && Object.keys(tool.inputSchema.properties).length > 0),
            requiredFieldsMarked: !!(tool.inputSchema && Array.isArray(tool.inputSchema.required)),
            hasOutputSchema: !!(tool.outputSchema),
            outputSchemaTyped: !!(tool.outputSchema && tool.outputSchema.type),
            hasMeta: !!(tool._meta),
            metaSurface: tool._meta?.surface || "MISSING",
            metaQueryEligible: tool._meta?.queryEligible !== undefined ? tool._meta.queryEligible : "MISSING",
            metaLatencyClass: tool._meta?.latencyClass || "MISSING",
            metaPricing: tool._meta?.pricing ? JSON.stringify(tool._meta.pricing) : "MISSING",
            metaRateLimit: tool._meta?.rateLimit ? "present" : "MISSING",
        };

        let hasExamples = false;
        let hasDefaults = false;
        if (tool.inputSchema && tool.inputSchema.properties) {
            const props = Object.values(tool.inputSchema.properties);
            hasExamples = props.some(p => p.examples || p.example);
            hasDefaults = props.some(p => p.default !== undefined);
        }
        audit.inputHasExamples = hasExamples;
        audit.inputHasDefaults = hasDefaults;

        auditResults.push(audit);

        console.log(`--- TOOL: ${tool.name} ---`);
        console.log(`Description: ${tool.description || "(none)"}`);
        console.log(`InputSchema: ${JSON.stringify(tool.inputSchema, null, 2)}`);
        console.log(`OutputSchema: ${JSON.stringify(tool.outputSchema, null, 2)}`);
        console.log(`_meta: ${JSON.stringify(tool._meta, null, 2)}`);
        console.log();
    }

    // SMOKE TESTS
    console.log("\n=== SMOKE TESTS ===\n");

    function generateSampleArgs(inputSchema) {
        if (!inputSchema || !inputSchema.properties) return {};
        const args = {};
        for (const [key, prop] of Object.entries(inputSchema.properties)) {
            if (prop.default !== undefined) {
                args[key] = prop.default;
            } else if (prop.examples && prop.examples.length > 0) {
                args[key] = prop.examples[0];
            } else if (prop.enum && prop.enum.length > 0) {
                args[key] = prop.enum[0];
            } else if (prop.type === "string") {
                const k = key.toLowerCase();
                if (k.includes("symbol") || k.includes("pair") || k.includes("currency") || k.includes("base") || k.includes("quote")) {
                    args[key] = "EUR/USD";
                } else if (k.includes("session")) {
                    args[key] = "london";
                } else if (k.includes("period") || k.includes("days") || k.includes("limit")) {
                    args[key] = "30";
                } else if (k.includes("interval")) {
                    args[key] = "1h";
                } else {
                    args[key] = "EUR/USD";
                }
            } else if (prop.type === "number" || prop.type === "integer") {
                args[key] = 30;
            } else if (prop.type === "boolean") {
                args[key] = false;
            } else if (prop.type === "array") {
                args[key] = [];
            }
        }
        return args;
    }

    const smokeResults = [];

    for (const tool of tools) {
        const sampleArgs = generateSampleArgs(tool.inputSchema);
        console.log(`Testing: ${tool.name}`);
        console.log(`  Args: ${JSON.stringify(sampleArgs)}`);
        const start = Date.now();
        try {
            const result = await client.callTool({ name: tool.name, arguments: sampleArgs });
            const elapsed = Date.now() - start;
            const hasContent = result.content && result.content.length > 0;
            const hasStructuredContent = !!result.structuredContent;
            const isError = result.isError === true;

            if (isError) {
                console.log(`  ❌ isError=true in ${elapsed}ms`);
            } else {
                console.log(`  ✅ Response in ${elapsed}ms | structuredContent: ${hasStructuredContent}`);
            }
            if (hasContent && result.content[0]) {
                const preview = typeof result.content[0].text === "string"
                    ? result.content[0].text.slice(0, 400)
                    : JSON.stringify(result.content[0]).slice(0, 400);
                console.log(`  Preview: ${preview}`);
            }
            if (hasStructuredContent) {
                console.log(`  StructuredContent keys: ${Object.keys(result.structuredContent).join(", ")}`);
            }

            smokeResults.push({
                name: tool.name,
                pass: !isError && hasContent,
                elapsed,
                hasStructuredContent,
                isError,
                errorMsg: isError ? (result.content?.[0]?.text || "unknown").slice(0, 120) : null,
            });
        } catch (err) {
            const elapsed = Date.now() - start;
            console.log(`  ❌ EXCEPTION after ${elapsed}ms: ${err.message}`);
            smokeResults.push({
                name: tool.name,
                pass: false,
                elapsed,
                hasStructuredContent: false,
                isError: true,
                errorMsg: err.message.slice(0, 120),
            });
        }
        console.log();
    }

    // FINAL SUMMARY TABLE
    console.log("\n=== FINAL SUMMARY TABLE ===\n");
    console.log("| Tool Name | Schema OK | Smoke Test | structuredContent | latency(ms) | Notes |");
    console.log("|-----------|-----------|------------|-------------------|-------------|-------|");

    for (let i = 0; i < tools.length; i++) {
        const a = auditResults[i];
        const s = smokeResults[i] || {};
        const schemaOk = a.hasDescription && a.inputSchemaTyped && a.requiredFieldsMarked && a.hasOutputSchema;
        const smokeOk = s.pass;
        const notes = [];
        if (!a.hasOutputSchema) notes.push("NO outputSchema");
        if (!a.hasMeta) notes.push("NO _meta");
        if (a.metaSurface === "MISSING") notes.push("_meta.surface MISSING");
        if (a.metaQueryEligible === "MISSING") notes.push("queryEligible MISSING");
        if (a.metaLatencyClass === "MISSING") notes.push("latencyClass MISSING");
        if (a.metaRateLimit === "MISSING") notes.push("rateLimit MISSING");
        if (!a.inputHasExamples) notes.push("no examples in inputSchema");
        if (!a.inputHasDefaults) notes.push("no defaults");
        if (s.isError) notes.push(`ERR: ${(s.errorMsg || "").slice(0, 80)}`);
        if (!s.hasStructuredContent) notes.push("no structuredContent");

        console.log(`| ${(a.name || "").padEnd(45)} | ${schemaOk ? "PASS" : "FAIL"} | ${smokeOk ? "PASS" : "FAIL"} | ${s.hasStructuredContent ? "YES" : "NO"} | ${s.elapsed || "?"} | ${notes.join("; ")} |`);
    }

    await client.close();
    console.log("\n=== PROBE COMPLETE ===");
}

main().catch(err => {
    console.error("Fatal error:", err);
    process.exit(1);
});
