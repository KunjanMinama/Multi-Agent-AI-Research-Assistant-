import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { Home } from './pages/Home';
import { History } from './pages/History';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background font-sans text-foreground flex flex-col selection:bg-primary/20">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
