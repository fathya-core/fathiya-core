CREATE TABLE public.ai_runs (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  task_id TEXT,
  model TEXT NOT NULL,
  system_prompt TEXT,
  user_prompt TEXT,
  output TEXT,
  saved_path TEXT,
  save_kind TEXT,
  status TEXT NOT NULL DEFAULT 'ok',
  error_message TEXT,
  http_status INTEGER,
  duration_ms INTEGER,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

ALTER TABLE public.ai_runs ENABLE ROW LEVEL SECURITY;

-- Public read access (no auth in project yet)
CREATE POLICY "ai_runs are viewable by everyone"
ON public.ai_runs
FOR SELECT
USING (true);

-- No INSERT/UPDATE/DELETE policies = only service role (server) can write

CREATE INDEX idx_ai_runs_created_at ON public.ai_runs (created_at DESC);
CREATE INDEX idx_ai_runs_task_id ON public.ai_runs (task_id);
CREATE INDEX idx_ai_runs_status ON public.ai_runs (status);