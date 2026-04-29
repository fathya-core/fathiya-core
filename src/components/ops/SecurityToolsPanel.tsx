import { useEffect, useState } from "react";
import { Shield, RefreshCw, ExternalLink, Loader2, Zap, Target, Search, Bug } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface SecurityTool {
  name: string;
  category: string;
  description: string;
  status: "available" | "running" | "error";
  lastUsed?: string;
}

interface HexstrikeStatus {
  connected: boolean;
  tools: SecurityTool[];
  serverVersion?: string;
  message?: string;
}

export function SecurityToolsPanel() {
  const [data, setData] = useState<HexstrikeStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      // Try to connect to HexStrike AI server health endpoint
      const response = await fetch("http://127.0.0.1:8888/health", {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const healthData = await response.json();

        // Convert tools_status to SecurityTool format
        const tools: SecurityTool[] = Object.entries(healthData.tools_status)
          .filter(([_, available]) => available === true)
          .map(([name, _]) => ({
            name: name as string,
            category: getToolCategory(name as string),
            description: `${name} - ${getToolCategory(name as string)}`,
            status: 'available' as const,
            lastUsed: undefined,
          }));

        setData({
          connected: true,
          tools: tools,
          serverVersion: healthData.version,
        });
      } else {
        throw new Error(`Server responded with ${response.status}`);
      }
    } catch (e) {
      setData({
        connected: false,
        tools: [],
        message: String(e)
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const getToolCategory = (toolName: string): string => {
    const categories: Record<string, string> = {
      // Network tools
      'nmap': 'Network Scanning',
      'masscan': 'Network Scanning',
      'rustscan': 'Network Scanning',
      'arp-scan': 'Network Scanning',
      'tcpdump': 'Network Analysis',
      'wireshark': 'Network Analysis',
      'tshark': 'Network Analysis',

      // Web tools
      'nikto': 'Web Security',
      'dirb': 'Web Discovery',
      'dirsearch': 'Web Discovery',
      'gobuster': 'Web Discovery',
      'feroxbuster': 'Web Discovery',
      'ffuf': 'Web Fuzzing',
      'wfuzz': 'Web Fuzzing',
      'sqlmap': 'Database Security',
      'dalfox': 'XSS Detection',

      // Binary analysis
      'objdump': 'Binary Analysis',
      'strings': 'Binary Analysis',
      'xxd': 'Binary Analysis',
      'gdb': 'Binary Analysis',
      'radare2': 'Binary Analysis',
      'checksec': 'Binary Security',

      // Password tools
      'hashcat': 'Password Cracking',
      'john': 'Password Cracking',
      'hydra': 'Password Cracking',
      'medusa': 'Password Cracking',

      // Wireless
      'aircrack-ng': 'Wireless Security',
      'airodump-ng': 'Wireless Security',
      'aireplay-ng': 'Wireless Security',

      // General
      'curl': 'HTTP Client',
      'file': 'File Analysis',
    };

    return categories[toolName] || 'Security Tool';
  };

  const getToolIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'network scanning':
      case 'network analysis':
        return <Search className="h-3 w-3" />;
      case 'web security':
      case 'web discovery':
      case 'web fuzzing':
        return <Target className="h-3 w-3" />;
      case 'binary analysis':
      case 'binary security':
        return <Bug className="h-3 w-3" />;
      case 'password cracking':
        return <Shield className="h-3 w-3" />;
      case 'wireless security':
        return <Zap className="h-3 w-3" />;
      default:
        return <Zap className="h-3 w-3" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'running':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'error':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      default:
        return 'text-muted-foreground bg-muted/20 border-border/40';
    }
  };

  const connected = !!data?.connected;

  // Compact mode when not connected
  if (!connected && !expanded) {
    return (
      <div className="mb-4 flex items-center justify-between gap-2 rounded border border-border/40 bg-muted/20 px-3 py-1.5 text-[10px]">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Shield className="h-3 w-3 text-rose-300/70" />
          <span>HexStrike AI: disconnected</span>
          {data?.message && <span className="text-rose-400">({data.message})</span>}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(true)}
          className="h-5 px-2 text-[9px] hover:bg-muted/40"
        >
          Configure
        </Button>
      </div>
    );
  }

  return (
    <Card className="mb-4 border-border/40 bg-card/30">
      <div className="p-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-red-500/30 bg-red-500/10">
              <Shield className="h-3.5 w-3.5 text-red-400" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-red-400">HexStrike AI Security Tools</h3>
              <p className="text-[9px] text-muted-foreground">
                {connected ? `${data.tools.length} of ${data.serverVersion ? data.serverVersion : '127'} tools available` : 'Security testing framework'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Badge
              variant="outline"
              className={`text-[9px] px-1.5 py-0.5 ${connected ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-rose-400 border-rose-500/30 bg-rose-500/10'}`}
            >
              {connected ? 'Connected' : 'Disconnected'}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={load}
              disabled={loading}
              className="h-6 w-6 p-0 hover:bg-muted/40"
            >
              {loading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <RefreshCw className="h-3 w-3" />
              )}
            </Button>
          </div>
        </div>

        {connected ? (
          <div className="space-y-2">
            {data.tools.slice(0, expanded ? undefined : 3).map((tool, i) => (
              <div key={i} className="flex items-center justify-between gap-2 rounded border border-border/30 bg-muted/10 px-2 py-1.5 text-[10px]">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <div className="flex h-4 w-4 items-center justify-center rounded border border-border/40 bg-muted/20">
                    {getToolIcon(tool.category)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-foreground truncate">{tool.name}</div>
                    <div className="text-muted-foreground truncate text-[9px]">{tool.description}</div>
                  </div>
                </div>
                <Badge
                  variant="outline"
                  className={`text-[8px] px-1 py-0 ${getStatusColor(tool.status)}`}
                >
                  {tool.status}
                </Badge>
              </div>
            ))}

            {data.tools.length > 3 && !expanded && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(true)}
                className="w-full h-6 text-[9px] hover:bg-muted/40"
              >
                Show all {data.tools.length} tools
              </Button>
            )}

            {expanded && (
              <div className="flex gap-2 pt-2 border-t border-border/30">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 h-7 text-[9px] border-red-500/30 text-red-400 hover:bg-red-500/10"
                  onClick={() => window.open('http://127.0.0.1:8888', '_blank')}
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  Open HexStrike UI
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setExpanded(false)}
                  className="h-7 px-2 text-[9px] hover:bg-muted/40"
                >
                  Collapse
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-center py-4">
              <Shield className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground mb-3">
                HexStrike AI server not detected
              </p>
              <p className="text-[9px] text-muted-foreground/70 mb-3">
                Start the HexStrike server to enable security testing tools
              </p>
              {data?.message && (
                <p className="text-[9px] text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded px-2 py-1">
                  {data.message}
                </p>
              )}
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={load}
                disabled={loading}
                className="flex-1 h-7 text-[9px] border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
              >
                {loading ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <RefreshCw className="h-3 w-3 mr-1" />
                )}
                Retry Connection
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(false)}
                className="h-7 px-2 text-[9px] hover:bg-muted/40"
              >
                Hide
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}