export const KNOWLEDGE_MISSION_PREFIX = "FATHIYA_KNOWLEDGE_MISSION_V1:";
export const MAX_KNOWLEDGE_OBJECTIVE_CHARACTERS = 2_000;
export const MAX_KNOWLEDGE_REPORT_CHARACTERS = 12_000;
export const MAX_KNOWLEDGE_SOURCE_CHARACTERS = 120;

export type KnowledgeMission = {
  source_name: string;
  objective: string;
  content: string;
};

export function buildKnowledgeMissionPrompt(mission: KnowledgeMission) {
  const sourceName = bounded(mission.source_name, "اسم المصدر", MAX_KNOWLEDGE_SOURCE_CHARACTERS);
  const objective = bounded(mission.objective, "الهدف", MAX_KNOWLEDGE_OBJECTIVE_CHARACTERS);
  const content = bounded(mission.content, "التقرير", MAX_KNOWLEDGE_REPORT_CHARACTERS);
  const prompt = `${KNOWLEDGE_MISSION_PREFIX}${JSON.stringify({
    source_name: sourceName,
    objective,
    content,
  })}`;
  if (prompt.length > 20_000) throw new Error("حجم مهمة التقرير يتجاوز الحد المسموح");
  return prompt;
}

export function parseKnowledgeMissionPrompt(prompt: string): KnowledgeMission | null {
  if (!prompt.startsWith(KNOWLEDGE_MISSION_PREFIX)) return null;
  try {
    const payload = JSON.parse(
      prompt.slice(KNOWLEDGE_MISSION_PREFIX.length),
    ) as Partial<KnowledgeMission>;
    if (
      typeof payload.source_name !== "string" ||
      typeof payload.objective !== "string" ||
      typeof payload.content !== "string"
    ) {
      return null;
    }
    return {
      source_name: payload.source_name,
      objective: payload.objective,
      content: payload.content,
    };
  } catch {
    return null;
  }
}

export function agentOperatorPrompt(prompt: string) {
  return parseKnowledgeMissionPrompt(prompt)?.objective ?? prompt;
}

function bounded(value: string, label: string, limit: number) {
  const clean = value.trim();
  if (clean.length < 3) throw new Error(`${label} يجب أن يحتوي على ثلاثة أحرف على الأقل`);
  if (clean.length > limit) throw new Error(`${label} يتجاوز ${limit} حرفًا`);
  return clean;
}
