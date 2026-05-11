export interface ResearchResponse {
  success: boolean;
  final_report: string;
  metadata: {
    iterations: number;
    quality_score: number;
    total_time: string;
    agents_used: string[];
  };
  errors?: string[];
}

export interface WSMessage {
  type: 'agent_update' | 'complete' | 'error';
  agent?: string;
  status?: 'waiting' | 'running' | 'complete' | 'error';
  message?: string;
  iteration?: number;
  timestamp?: string;
  final_report?: string;
  metadata?: any;
}

export interface HistoryItem {
  id: string;
  query: string;
  date: string;
  report: string;
  metadata: any;
}
