import { useState, useEffect, useRef } from 'react';
import { Play, AlertCircle } from 'lucide-react';
import { QueryInput } from '../components/QueryInput';
import { FileUpload } from '../components/FileUpload';
import { AgentVisualization } from '../components/AgentVisualization';
import { ReportViewer } from '../components/ReportViewer';
import { Button } from '../components/ui/button';
import { useWebSocket } from '../hooks/useWebSocket';
import { submitResearch } from '../lib/api';
import type { ResearchResponse, HistoryItem } from '../lib/types';
import { useLocalStorage } from '../hooks/useLocalStorage';

export function Home() {
  const [query, setQuery] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [report, setReport] = useState<ResearchResponse | null>(null);
  const [history, setHistory] = useLocalStorage<HistoryItem[]>('research_history', []);
  const [iteration, setIteration] = useState(0);
  const statusRef = useRef(status); // ref to avoid stale closure in async callbacks
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/stream';
  const { messages, connect, disconnect, clearMessages } = useWebSocket(WS_URL);

  useEffect(() => {
    if (status === 'running') {
      connect();
    } else {
      disconnect();
      // Clear timeout on any status change away from running
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    }
  }, [status]);

  useEffect(() => {
    if (messages.length > 0) {
      const latest = messages[messages.length - 1];
      if (latest.iteration) setIteration(latest.iteration);
      if (latest.type === 'complete' && latest.final_report) {
        setStatus('complete');
        const result: ResearchResponse = {
          success: true,
          final_report: latest.final_report,
          metadata: latest.metadata || {
            iterations: latest.iteration ?? 0,
            quality_score: 0.9,
            total_time: 'Unknown',
            agents_used: []
          }
        };
        setReport(result);
        setHistory(prev => [{
          id: Date.now().toString(),
          query,
          date: new Date().toISOString(),
          report: result.final_report,
          metadata: result.metadata
        }, ...prev]);
      } else if (latest.type === 'error') {
        setStatus('error');
        setErrorMsg(latest.message || 'An error occurred during execution.');
      }
    }
  }, [messages]);

  const handleStart = async () => {
    if (!query.trim()) return;

    setStatus('running');
    setErrorMsg('');
    setReport(null);
    clearMessages();
    setIteration(0);

    // Set a 120 second timeout in case backend hangs silently
    timeoutRef.current = setTimeout(() => {
      if (statusRef.current === 'running') {
        setStatus('error');
        setErrorMsg('Request timed out (120s). The research backend may be starting up — please try again in a moment.');
      }
    }, 120_000);

    try {
      const res = await submitResearch(query, file || undefined);
      // Use ref (not state) to avoid stale closure
      if (res.success && statusRef.current !== 'complete') {
        setReport(res);
        setStatus('complete');
        setHistory(prev => [{
          id: Date.now().toString(),
          query,
          date: new Date().toISOString(),
          report: res.final_report,
          metadata: res.metadata
        }, ...prev]);
      }
    } catch (err: any) {
      if (statusRef.current === 'running') {
        setStatus('error');
        setErrorMsg(
          err.message?.includes('Failed to fetch')
            ? 'Cannot reach the backend. Check that VITE_API_URL is set correctly in Vercel.'
            : (err.message || 'Failed to connect to research backend.')
        );
      }
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setQuery('');
    setFile(null);
    setReport(null);
    clearMessages();
  };

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const isLocalhost = apiUrl.includes('localhost');

  return (
    <div className="container py-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">

      {/* Warning banner if env vars not configured */}
      {isLocalhost && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-700 dark:text-yellow-400">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <p className="text-sm font-medium">
            <strong>Dev mode:</strong> API is pointing to localhost. Set <code>VITE_API_URL</code> and <code>VITE_WS_URL</code> in Vercel to connect to your Railway backend.
          </p>
        </div>
      )}

      {status === 'idle' && (
        <div className="space-y-8">
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
              Multi-Agent Research System
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Harness the power of specialized AI agents to analyze data, research topics, and synthesize comprehensive reports.
            </p>
          </div>

          <div className="bg-card p-6 md:p-8 rounded-2xl shadow-lg border border-primary/10 space-y-6">
            <QueryInput
              value={query}
              onChange={setQuery}
              onSubmit={handleStart}
              disabled={false}
            />

            <FileUpload
              onFileSelect={setFile}
              disabled={false}
            />

            <Button
              size="lg"
              className="w-full text-lg h-14"
              onClick={handleStart}
              disabled={!query.trim()}
            >
              <Play className="mr-2 h-5 w-5" />
              Start Research
            </Button>
          </div>
        </div>
      )}

      {status === 'running' && (
        <div className="max-w-3xl mx-auto space-y-8">
          <div className="text-center space-y-2">
            <h2 className="text-2xl font-bold">Research in Progress</h2>
            <p className="text-muted-foreground">
              Our agents are working on your query — this may take 30–90 seconds...
            </p>
          </div>
          <AgentVisualization
            messages={messages}
            iteration={iteration}
            totalIterations={5}
          />
          <div className="flex justify-center">
            <Button variant="outline" size="sm" onClick={handleReset}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {status === 'complete' && report && (
        <div className="space-y-8">
          <ReportViewer report={report.final_report} metadata={report.metadata} />
          <div className="flex justify-center">
            <Button size="lg" variant="outline" onClick={handleReset}>
              Start New Research
            </Button>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="text-center space-y-6 p-8 bg-destructive/10 rounded-2xl border border-destructive/20 max-w-2xl mx-auto">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="text-2xl font-bold text-destructive">Research Failed</h2>
          <p className="text-muted-foreground">{errorMsg}</p>
          <Button size="lg" variant="default" onClick={handleReset}>
            Try Again
          </Button>
        </div>
      )}

    </div>
  );
}
