import { Link } from 'react-router-dom';
import { Brain, History, Sun, Moon } from 'lucide-react';
import { Button } from './ui/button';
import { useEffect, useState } from 'react';

export function Header() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" className="flex items-center gap-2 transition-opacity hover:opacity-80">
          <div className="bg-primary text-primary-foreground p-1.5 rounded-lg">
            <Brain className="h-6 w-6" />
          </div>
          <span className="font-bold text-xl tracking-tight hidden sm:inline-block">
            Nexus Research
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <nav className="flex items-center gap-1 sm:gap-2">
            <Link to="/history">
              <Button variant="ghost" size="sm" className="gap-2">
                <History className="h-4 w-4" />
                <span className="hidden sm:inline">History</span>
              </Button>
            </Link>
            <Button variant="ghost" size="icon" onClick={() => setIsDark(!isDark)}>
              {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </nav>
        </div>
      </div>
    </header>
  );
}
