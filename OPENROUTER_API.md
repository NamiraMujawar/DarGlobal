# OpenRouter API reference

**Author:** Namira Mujawar · **Project date:** 2026-11-18

## Important: rotate exposed keys

Never save an API key in source code, examples, chat messages, or screenshots. If a
key has been shared, revoke it in the OpenRouter dashboard and create a replacement:
<https://openrouter.ai/keys>.

The key previously shared in chat is intentionally **not** included in this file or
in the project's `.env`. Put a newly generated key in your local, git-ignored `.env`:

```dotenv
OPENROUTER_API_KEY=PASTE_YOUR_NEW_KEY_HERE
OPENROUTER_MODEL=openrouter/free
```

Restart `app.py` after saving `.env`. The Python app reads the key on startup and
sends it from the server; browser JavaScript never receives it. Keep `.env` private.

## TypeScript example

Use the placeholder below only as a template. Do not put a real key in client-side
browser code; a browser bundle exposes it to every visitor. The chatbot in this
project calls OpenRouter from its Python server instead.

```typescript
const apiKey = process.env.OPENROUTER_API_KEY;
if (!apiKey) {
  throw new Error("Set OPENROUTER_API_KEY in the server environment.");
}

const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "DarGlobal & Wasalt Research Assistant",
  },
  body: JSON.stringify({
    model: process.env.OPENROUTER_MODEL ?? "openrouter/free",
    messages: [
      { role: "user", content: "What is the meaning of life?" },
    ],
  }),
});

if (!response.ok) {
  throw new Error(`OpenRouter request failed: HTTP ${response.status}`);
}

const result = await response.json();
console.log(result.choices[0].message.content);
```

## REST / cURL example

The key is read from the environment variable rather than typed into the command:

```sh
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "openrouter/free",
    "messages": [
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
  }'
```

In Windows PowerShell, set the variable for the current terminal before using cURL:

```powershell
$env:OPENROUTER_API_KEY = "PASTE_YOUR_NEW_KEY_HERE"
curl.exe https://openrouter.ai/api/v1/chat/completions `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $env:OPENROUTER_API_KEY" `
  -d '{"model":"openrouter/free","messages":[{"role":"user","content":"What is the meaning of life?"}]}'
```

## Model and cost note

The original `openai/gpt-4o` example is not guaranteed to be free and may require
available OpenRouter account credits. The chatbot defaults to `openrouter/free`;
check the model catalogue and your account's pricing/limits before selecting another
model: <https://openrouter.ai/models>.
