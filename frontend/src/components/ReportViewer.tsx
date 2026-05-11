import ReactMarkdown from 'react-markdown';
import { Copy, Download, FileDown, Share } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import jsPDF from 'jspdf';
import type { ResearchResponse } from '../lib/types';

interface ReportViewerProps {
  report: string;
  metadata: ResearchResponse['metadata'];
}

export function ReportViewer({ report, metadata }: ReportViewerProps) {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(report);
  };

  const downloadMarkdown = () => {
    const blob = new Blob([report], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'research-report.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadPDF = () => {
    // Basic PDF generation (for complete rendering, a more complex setup is needed like html2pdf)
    const doc = new jsPDF();
    const splitText = doc.splitTextToSize(report, 180);
    doc.text(splitText, 15, 15);
    doc.save('research-report.pdf');
  };

  const shareReport = () => {
    if (navigator.share) {
      navigator.share({
        title: 'Research Report',
        text: report.substring(0, 100) + '...',
      });
    } else {
      copyToClipboard();
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <h2 className="text-3xl font-bold tracking-tight">Research Report</h2>
        
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={copyToClipboard}>
            <Copy className="h-4 w-4 mr-2" />
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={downloadMarkdown}>
            <Download className="h-4 w-4 mr-2" />
            Download MD
          </Button>
          <Button variant="outline" size="sm" onClick={downloadPDF}>
            <FileDown className="h-4 w-4 mr-2" />
            Download PDF
          </Button>
          <Button variant="outline" size="sm" onClick={shareReport}>
            <Share className="h-4 w-4 mr-2" />
            Share
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 flex flex-col justify-center items-center text-center bg-card shadow-sm border-primary/10">
          <p className="text-sm font-medium text-muted-foreground mb-1">Quality Score</p>
          <p className="text-3xl font-bold text-primary">
            {(metadata.quality_score * 100).toFixed(0)}%
          </p>
        </Card>
        <Card className="p-5 flex flex-col justify-center items-center text-center bg-card shadow-sm border-primary/10">
          <p className="text-sm font-medium text-muted-foreground mb-1">Iterations</p>
          <p className="text-3xl font-bold text-primary">{metadata.iterations}</p>
        </Card>
        <Card className="p-5 flex flex-col justify-center items-center text-center bg-card shadow-sm border-primary/10">
          <p className="text-sm font-medium text-muted-foreground mb-1">Time Taken</p>
          <p className="text-3xl font-bold text-primary">{metadata.total_time}</p>
        </Card>
        <Card className="p-5 flex flex-col justify-center items-center text-center bg-card shadow-sm border-primary/10">
          <p className="text-sm font-medium text-muted-foreground mb-1">Agents Used</p>
          <p className="text-3xl font-bold text-primary">{metadata.agents_used.length}</p>
        </Card>
      </div>

      {/* Markdown Report */}
      <Card className="p-8 shadow-md border-border bg-card">
        <div className="prose prose-slate dark:prose-invert max-w-none w-full">
          <ReactMarkdown
          components={{
            h1: ({node, ...props}) => <h1 className="text-3xl font-bold mt-6 mb-4 pb-2 border-b" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-2xl font-semibold mt-8 mb-4 pb-2 border-b" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-xl font-semibold mt-6 mb-3" {...props} />,
            p: ({node, ...props}) => <p className="leading-relaxed mb-4 text-foreground/90" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-2" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-2" {...props} />,
            li: ({node, ...props}) => <li className="text-foreground/90" {...props} />,
            code({ node, inline, className, children, ...props }: any) {
              return inline ? (
                <code className="bg-muted px-1.5 py-0.5 rounded-md text-sm font-mono text-primary" {...props}>
                  {children}
                </code>
              ) : (
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto border border-border my-4">
                  <code className="text-sm font-mono text-foreground/90" {...props}>{children}</code>
                </pre>
              );
            }
          }}
        >
          {report}
          </ReactMarkdown>
        </div>
      </Card>
    </div>
  );
}
