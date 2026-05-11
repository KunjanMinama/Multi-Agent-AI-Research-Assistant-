import { useState, useCallback, useRef, useEffect } from 'react';
import type { WSMessage } from '../lib/types';

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<WSMessage[]>([]);
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed'>('closed');
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    setStatus('connecting');
    wsRef.current = new WebSocket(url);
    
    wsRef.current.onopen = () => {
      setStatus('open');
    };

    wsRef.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        setMessages(prev => [...prev, message]);
      } catch (e) {
        console.error('Failed to parse message', e);
      }
    };

    wsRef.current.onclose = () => {
      setStatus('closed');
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('closed');
    };
  }, [url]);

  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    setStatus('closed');
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { messages, status, connect, disconnect, sendMessage, clearMessages };
}
