import { useLocalStorage } from '../hooks/useLocalStorage';
import type { HistoryItem } from '../lib/types';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Link } from 'react-router-dom';
import { ArrowLeft, Trash2, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { ReportViewer } from '../components/ReportViewer';

export function History() {
  const [history, setHistory] = useLocalStorage<HistoryItem[]>('research_history', []);
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const clearHistory = () => {
    if (confirm('Are you sure you want to clear all history?')) {
      setHistory([]);
      setSelectedItem(null);
    }
  };

  if (selectedItem) {
    return (
      <div className="container py-8 max-w-5xl mx-auto space-y-6 animate-in slide-in-from-right-8 duration-300">
        <Button variant="ghost" onClick={() => setSelectedItem(null)} className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to History
        </Button>
        <div className="mb-8">
          <h2 className="text-xl font-medium text-muted-foreground mb-2">Original Query:</h2>
          <p className="text-2xl font-semibold">{selectedItem.query}</p>
        </div>
        <ReportViewer report={selectedItem.report} metadata={selectedItem.metadata} />
      </div>
    );
  }

  return (
    <div className="container py-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Research History</h1>
          <p className="text-muted-foreground mt-1">View your past queries and generated reports.</p>
        </div>
        {history.length > 0 && (
          <Button variant="destructive" size="sm" onClick={clearHistory}>
            <Trash2 className="mr-2 h-4 w-4" />
            Clear All
          </Button>
        )}
      </div>

      {history.length === 0 ? (
        <Card className="p-12 text-center border-dashed">
          <h3 className="text-xl font-medium mb-2">No history yet</h3>
          <p className="text-muted-foreground mb-6">You haven't run any research queries yet.</p>
          <Link to="/">
            <Button>Start Your First Research</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <Card 
              key={item.id} 
              className="p-5 flex justify-between items-center hover:bg-accent/50 transition-colors cursor-pointer group"
              onClick={() => setSelectedItem(item)}
            >
              <div className="space-y-1 overflow-hidden pr-4">
                <p className="font-semibold truncate text-lg group-hover:text-primary transition-colors">
                  {item.query}
                </p>
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>{new Date(item.date).toLocaleDateString()} {new Date(item.date).toLocaleTimeString()}</span>
                  <span>•</span>
                  <span>Score: {(item.metadata?.quality_score * 100 || 0).toFixed(0)}%</span>
                </div>
              </div>
              <Button variant="ghost" size="icon" className="shrink-0">
                <ChevronRight className="h-5 w-5" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
