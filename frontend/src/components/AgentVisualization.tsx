import { Brain, Search, BarChart, Combine, FileText, CheckCircle, Loader2, Circle, XCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { Card } from './ui/card';
import { Progress } from './ui/progress';
import { cn } from '../lib/utils';
import type { WSMessage } from '../lib/types';

interface AgentVisualizationProps {
  messages: WSMessage[];
  iteration: number;
  totalIterations: number;
}

interface AgentInfo {
  name: string;
  id: string;
  icon: any;
}

const AGENTS: AgentInfo[] = [
  { name: 'Planner', id: 'planner', icon: Brain },
  { name: 'Researcher', id: 'researcher', icon: Search },
  { name: 'Data Analyst', id: 'data_analyst', icon: BarChart },
  { name: 'Synthesizer', id: 'synthesizer', icon: Combine },
  { name: 'Writer', id: 'writer', icon: FileText }
];

export function AgentVisualization({ 
  messages, 
  iteration, 
  totalIterations 
}: AgentVisualizationProps) {
  
  // Calculate status for each agent based on messages
  const getAgentStatus = (agentId: string) => {
    // Find the latest message for this agent
    const agentMessages = messages.filter(m => m.agent === agentId);
    if (agentMessages.length === 0) return { status: 'waiting', message: 'Waiting...' };
    
    const latest = agentMessages[agentMessages.length - 1];
    return { status: latest.status || 'waiting', message: latest.message };
  };

  return (
    <Card className="p-6 border-primary/20 shadow-lg">
      <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        Agent Pipeline
      </h3>
      
      <div className="space-y-4">
        {AGENTS.map((agent, i) => {
          const { status, message } = getAgentStatus(agent.id);
          return (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={cn(
                "flex items-center gap-4 p-4 rounded-xl transition-all duration-300",
                status === 'running' ? "bg-primary/5 border border-primary/30 shadow-sm" : "border border-transparent",
                status === 'complete' ? "bg-accent/50" : ""
              )}
            >
              {/* Status Icon */}
              {status === 'complete' && (
                <CheckCircle className="h-6 w-6 text-green-500" />
              )}
              {status === 'running' && (
                <Loader2 className="h-6 w-6 text-primary animate-spin" />
              )}
              {status === 'waiting' && (
                <Circle className="h-6 w-6 text-muted-foreground/50" />
              )}
              {status === 'error' && (
                <XCircle className="h-6 w-6 text-destructive" />
              )}

              {/* Agent Icon */}
              <div className={cn(
                "p-2 rounded-lg",
                status === 'running' ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
              )}>
                <agent.icon className="h-5 w-5" />
              </div>

              {/* Agent Name */}
              <span className="font-semibold text-foreground">{agent.name}</span>

              {/* Status Message */}
              {message && (
                <span className="text-sm text-muted-foreground ml-auto max-w-[200px] truncate">
                  {message}
                </span>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div className="mt-8 space-y-3">
        <div className="flex justify-between text-sm font-medium text-muted-foreground">
          <span>Iteration {iteration} of {totalIterations}</span>
          <span>{Math.round((iteration / totalIterations) * 100)}%</span>
        </div>
        <Progress value={(iteration / totalIterations) * 100} className="h-2" />
      </div>
    </Card>
  );
}
