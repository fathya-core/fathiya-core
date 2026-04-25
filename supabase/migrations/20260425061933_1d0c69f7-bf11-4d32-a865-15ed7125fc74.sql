CREATE TABLE public.security_scans (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  scan_id text NOT NULL UNIQUE,
  scan_type text NOT NULL,
  target text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  findings jsonb NOT NULL DEFAULT '[]'::jsonb,
  report_markdown text,
  report_url text,
  notified boolean NOT NULL DEFAULT false,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now()
);

ALTER TABLE public.security_scans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "security_scans are viewable by everyone"
ON public.security_scans FOR SELECT USING (true);

CREATE INDEX idx_security_scans_scan_id ON public.security_scans(scan_id);
CREATE INDEX idx_security_scans_status ON public.security_scans(status);