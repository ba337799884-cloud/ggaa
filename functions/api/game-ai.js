const MODEL = "@cf/meta/llama-3.1-8b-instruct";
const MAX_BODY_BYTES = 10 * 1024;
const MAX_REQUESTS_PER_WINDOW = 5;
const WINDOW_MS = 60_000;

// Soft per-isolate request throttling. Configure platform-level rate limiting for strong global protection.
const requestBuckets = new Map();

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "same-origin",
    },
  });
}

function allowedOrigin(request) {
  const origin = request.headers.get("Origin");
  if (!origin) return false;
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

function softRateLimit(request) {
  const now = Date.now();
  // IP is used transiently for throttling and is not sent to the model or logged here.
  const key = request.headers.get("CF-Connecting-IP") || "unknown";
  let bucket = requestBuckets.get(key);

  if (!bucket || now - bucket.start >= WINDOW_MS) {
    bucket = { start: now, count: 0 };
    requestBuckets.set(key, bucket);
  }

  bucket.count += 1;

  if (requestBuckets.size > 500) {
    for (const [id, value] of requestBuckets) {
      if (now - value.start >= WINDOW_MS) requestBuckets.delete(id);
      if (requestBuckets.size <= 400) break;
    }
  }

  return bucket.count <= MAX_REQUESTS_PER_WINDOW;
}

function cleanText(value, maxLength = 800) {
  return typeof value === "string" ? value.slice(0, maxLength) : "";
}

function validatePayload(input) {
  const device = input && typeof input.device === "object" && input.device
    ? input.device
    : {};

  const numberOrNull = (value, max) =>
    Number.isFinite(value) && value >= 0 && value <= max ? value : null;

  return {
    profile: cleanText(input?.profile, 100) || "Unknown",
    fps: numberOrNull(input?.fps, 360),
    issue: cleanText(input?.issue, 800) || "No runtime error was provided.",
    device: {
      memoryGb: numberOrNull(device.memoryGb, 1024),
      cpuThreads: numberOrNull(device.cpuThreads, 512),
      webgpu: device.webgpu === true,
      crossOriginIsolated: device.crossOriginIsolated === true,
      graphicsPlus: device.graphicsPlus === true,
      screenWidth: numberOrNull(device.screenWidth, 20000),
      screenHeight: numberOrNull(device.screenHeight, 20000),
      devicePixelRatio: numberOrNull(device.devicePixelRatio, 10),
    },
  };
}

function parseModelAnswer(result) {
  const raw = typeof result === "string"
    ? result
    : result?.response ?? result?.output_text ?? result?.output ?? "";

  if (typeof raw !== "string" || raw.length === 0) {
    throw new Error("The AI model returned an empty response.");
  }

  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start < 0 || end <= start) {
    throw new Error("The AI model did not return the expected JSON answer.");
  }

  const parsed = JSON.parse(raw.slice(start, end + 1));
  const profiles = new Set(["efficiency", "balanced", "quality"]);
  const profile = profiles.has(parsed.profile) ? parsed.profile : "balanced";
  const advice = cleanText(parsed.advice, 1400).trim();

  if (!advice) throw new Error("The AI model returned no actionable advice.");
  return { profile, advice };
}

export async function onRequestPost({ request, env }) {
  if (!allowedOrigin(request)) {
    return json({ ok: false, error: "Same-origin requests only." }, 403);
  }

  if (request.headers.get("content-type")?.split(";")[0].trim() !== "application/json") {
    return json({ ok: false, error: "Send a JSON request." }, 415);
  }

  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BODY_BYTES) {
    return json({ ok: false, error: "Request is too large." }, 413);
  }

  if (!softRateLimit(request)) {
    return json({ ok: false, error: "Too many AI requests. Please wait a minute and try again." }, 429);
  }

  if (!env || !env.AI || typeof env.AI.run !== "function") {
    return json({
      ok: false,
      error: "Workers AI is not configured for this Pages project. Add a Workers AI binding named AI and redeploy.",
    }, 503);
  }

  let bodyText;
  try {
    bodyText = await request.text();
  } catch {
    return json({ ok: false, error: "Could not read the request body." }, 400);
  }

  if (new TextEncoder().encode(bodyText).byteLength > MAX_BODY_BYTES) {
    return json({ ok: false, error: "Request is too large." }, 413);
  }

  let input;
  try {
    input = JSON.parse(bodyText);
  } catch {
    return json({ ok: false, error: "The request was not valid JSON." }, 400);
  }

  const safeInput = validatePayload(input);

  const systemPrompt = [
    "You are Game Performance Coach, a technical assistant for a WebGPU/WebAssembly open-world driving game.",
    "Give practical, conservative graphics and performance advice. Do not claim to inspect rendered frames, source files, gameplay footage, or hardware telemetry beyond the JSON the user supplies.",
    "Choose profile 'efficiency' for weak or unstable capability / low FPS, 'quality' only for strong capabilities, otherwise 'balanced'.",
    "Explain trade-offs clearly. A 60 FPS value is a target, not a guarantee. Do not claim this browser game has NVIDIA DLSS, neural rendering, hardware ray tracing, or Forza Horizon features unless input establishes it.",
    "Return ONLY a JSON object with two fields: profile (one of efficiency, balanced, quality) and advice (a short plain-language recommendation under 1400 characters).",
  ].join(" ");

  const userPrompt = "Analyze these bounded device hints and current game status. Recommend a safe profile and practical next steps. Input JSON: " +
    JSON.stringify(safeInput);

  try {
    const modelResult = await env.AI.run(MODEL, {
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 380,
      temperature: 0.2,
    });

    const answer = parseModelAnswer(modelResult);
    return json({
      ok: true,
      ...answer,
      model: MODEL,
    });
  } catch {
    return json({
      ok: false,
      error: "The AI model did not complete this request. You can still use the Smart Performance Advisor and Safe Mode.",
    }, 502);
  }
}

export async function onRequestGet() {
  return json({ ok: false, error: "Use POST to request a game performance analysis." }, 405);
}
