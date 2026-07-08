/**
 * AI Security Gateway — TypeScript port for Portal BFF.
 * Checks incoming chat messages for prompt injection, jailbreak, DLP.
 */
const INJECTION_PATTERNS: RegExp[] = [
  // System prompt override
  /ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|messages?)/i,
  /forget\s+(all\s+)?(previous|prior|your)\s+(instructions?|prompts?|training)/i,
  /you\s+are\s+now\s+(a\s+)?(DAN|jailbroken|unfiltered|unrestricted)/i,
  /system\s*(prompt|message|instruction)\s*(is|:)?\s*['"]/i,
  /pretend\s+(you\s+are|to\s+be)\s+(a\s+)?(different|another|new)/i,
  // Role override
  /(new|override|replace)\s+(system|your)\s+(prompt|role|instruction|personality)/i,
  /from\s+now\s+on\s+you\s+(are|will\s+be|must)/i,
  /disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|constraints?|rules?)/i,
  // Jailbreak (expanded)
  /(DAN|developer\s*mode|god\s*mode|chaos\s*mode)\s*(mode|enabled|activated)/i,
  /you\s+have\s+(no|zero|unlimited)\s+(restrictions?|constraints?|limits?|rules?)/i,
  /(bypass|circumvent|override)\s+(your|the)\s+(restrictions?|safety|filters?)/i,
  /act\s+as\s+(an\s+)?(unethical|unrestricted|unfiltered|unhinged)/i,
  /(you|now)\s+(are|become)\s+(evil|malicious|dark|rogue)/i,
  /\[system\]\s*\(override/i,
  // Token smuggling
  /respond\s+in\s+base64/i,
  /decode\s+this\s+(base64|hex|encoded)/i,
  // Prompt leaking
  /(tell|show|repeat|output|print|display)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?)/i,
  /(begin|start)\s+(your|every)\s+(response|message)\s+with/i,
  // Russian jailbreak
  /игнорируй\s+(вс[её]\s+)?(предыдущие|прошлые)\s+(инструкции|правила|ограничения)/i,
  /забудь\s+(вс[её]|свои)\s+(инструкции|правила|ограничения|промпт)/i,
  /ты\s+теперь\s+(злой|свободный|без\s+ограничений|взломан)/i,
  /расскажи\s+(мне\s+)?(свои|твои)\s+(системные\s+)?(инструкции|промпты|настройки)/i,
  /напиши\s+(мне\s+)?(свой|твой)\s+(системный\s+)?(промпт|инструкцию)/i,
  /смени\s+(свою|твою)\s+(роль|личность|маску)/i,
];

const DLP_PATTERNS: [RegExp, string][] = [
  // Credit cards
  [/\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b/, "credit_card"],
  // Russian passport
  [/\b\d{2}\s?\d{2}\s?\d{6}\b/, "passport_rf"],
  // Russian SNILS (СНИЛС: XXX-XXX-XXX YY or XXXXXXXXXYY)
  [/\b\d{3}[-]?\d{3}[-]?\d{3}\s?\d{2}\b/, "snils"],
  // Russian INN (ИНН: 10 or 12 digits)
  [/\b\d{10}(?:\d{2})?\b/, "inn"],
  // SSN (US)
  [/\b\d{3}-\d{2}-\d{4}\b/, "ssn"],
  // Phone (Russian)
  [/(?<!\w)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\w)/, "phone_ru"],
  // Email
  [/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, "email"],
  // API keys
  [/\b(sk-[A-Za-z0-9]{32,}|hf_[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{32,}|xai-[A-Za-z0-9]{32,})\b/, "api_key"],
  // AWS keys
  [/\bAKIA[0-9A-Z]{16}\b/, "aws_key"],
  // Internal IPs
  [/\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b/, "internal_ip"],
];

export interface SecurityCheckResult {
  ok: boolean;
  reason: string;
  category: "clean" | "prompt_injection" | "dlp";
}

export function checkSecurity(messages: { role: string; content: string }[]): SecurityCheckResult {
  // 1. Prompt injection check
  for (const msg of messages) {
    const content = typeof msg.content === "string" ? msg.content : "";
    if (!content) continue;
    for (const pattern of INJECTION_PATTERNS) {
      if (pattern.test(content)) {
        return { ok: false, reason: `prompt_injection: ${pattern.source.slice(0, 60)}`, category: "prompt_injection" };
      }
    }
  }

  // 2. DLP check
  for (const msg of messages) {
    const content = typeof msg.content === "string" ? msg.content : "";
    if (!content) continue;
    for (const [pattern, label] of DLP_PATTERNS) {
      const match = pattern.exec(content);
      if (match) {
        return { ok: false, reason: `dlp_${label}`, category: "dlp" };
      }
    }
  }

  return { ok: true, reason: "", category: "clean" };
}
