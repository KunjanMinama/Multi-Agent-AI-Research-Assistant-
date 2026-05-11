const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function submitResearch(query: string, file?: File) {
  if (file) {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/research-with-data`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) throw new Error('Research failed');
    return response.json();
  } else {
    const response = await fetch(`${API_BASE}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query })
    });

    if (!response.ok) throw new Error('Research failed');
    return response.json();
  }
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
