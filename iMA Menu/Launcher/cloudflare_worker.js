/**
 * Cloudflare Worker: iMA Menu Error & Crash Telemetry Proxy
 * 
 * Safely forwards application errors to Discord without exposing the webhook URL
 * in client executables or triggering antivirus / heuristic flags.
 * 
 * Deployment (One-Click):
 * 1. Log in to https://dash.cloudflare.com/
 * 2. Go to "Workers & Pages" -> "Create Application" -> "Create Worker"
 * 3. Give it a name (e.g., "ima-menu-telemetry") -> Click "Deploy"
 * 4. Click "Edit Code" -> Paste this entire script -> Click "Deploy"
 * 5. (Optional) In Settings -> Variables, add DISCORD_WEBHOOK_URL as an Encrypted Secret.
 */

const DEFAULT_WEBHOOK_URL = "https://discord.com/api/webhooks/1566181677770874910/MpIa_7IbfmuwOEoDXrsP8BjoJRqifxPxEHYLChiLMO05Rru8MXDILHyqqoaIXrYohrYj";

// In-memory deduplication cache (per Cloudflare edge instance)
const rateLimitCache = new Map();

export default {
  async fetch(request, env, ctx) {
    // 1. Handle CORS Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, X-Telemetry-Token",
        },
      });
    }

    // 2. Only accept POST
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" },
      });
    }

    try {
      const payload = await request.json();
      const webhookUrl = env.DISCORD_WEBHOOK_URL || DEFAULT_WEBHOOK_URL;

      if (!webhookUrl) {
        return new Response(JSON.stringify({ error: "Missing Discord webhook URL" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        });
      }

      // Extract error fields
      const app = payload.app || "iMA Menu Launcher";
      const version = payload.version || "Unknown";
      const errorType = payload.error_type || "UnhandledException";
      let message = payload.message || "An unexpected error occurred.";
      let traceback = payload.traceback || "";
      const osInfo = payload.os || "Windows";
      const timestamp = payload.timestamp || new Date().toISOString();

      // 3. Scrub PII (Windows username, user profile paths, tokens)
      const scrubPII = (str) => {
        if (!str || typeof str !== "string") return str;
        return str
          // Scrub C:\Users\<Username>\ to C:\Users\<user>\
          .replace(/([a-zA-Z]:[\\/]+Users[\\/]+)[^\\/\r\n]+/gi, "$1<user>")
          .replace(/(\/home\/)[^\/\r\n]+/gi, "$1<user>")
          // Scrub token / credential patterns
          .replace(/(token|secret|password|bearer|auth)[=:\s]+[A-Za-z0-9_\-\.]{8,}/gi, "$1=***REDACTED***");
      };

      message = scrubPII(message);
      traceback = scrubPII(traceback);

      // 4. Rate-limiting & deduplication (cooldown 30s per unique error fingerprint)
      const errorKey = `${app}:${version}:${errorType}:${message.slice(0, 100)}`;
      const now = Date.now();
      const lastSeen = rateLimitCache.get(errorKey);
      if (lastSeen && (now - lastSeen) < 30000) {
        return new Response(JSON.stringify({ status: "skipped", reason: "rate_limited" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      rateLimitCache.set(errorKey, now);

      // 5. Format Discord Rich Embed
      let formattedTrace = traceback;
      if (formattedTrace.length > 1800) {
        formattedTrace = formattedTrace.slice(0, 1800) + "\n... [truncated]";
      }

      const discordBody = {
        username: "iMA Diagnostics",
        avatar_url: "https://raw.githubusercontent.com/iMAboud/iMA-Menu-Plugins/main/Assets/ima.png",
        embeds: [
          {
            title: `🚨 ${errorType}`,
            description: formattedTrace ? `\`\`\`python\n${formattedTrace}\n\`\`\`` : `\`\`\`\n${message}\n\`\`\``,
            color: 0xED8796, // Soft Catppuccin Coral/Red
            fields: [
              { name: "App", value: `\`${app}\``, inline: true },
              { name: "Version", value: `\`v${version}\``, inline: true },
              { name: "Platform", value: `\`${osInfo}\``, inline: true },
              { name: "Message", value: message.slice(0, 500) || "N/A", inline: false },
            ],
            footer: {
              text: `iMA Menu Telemetry • ${timestamp}`,
            },
            timestamp: new Date().toISOString(),
          },
        ],
      };

      // 6. Forward to Discord
      const discordResponse = await fetch(webhookUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(discordBody),
      });

      if (!discordResponse.ok) {
        const errorText = await discordResponse.text();
        return new Response(JSON.stringify({ error: "Discord webhook failed", details: errorText }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });

    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  },
};
