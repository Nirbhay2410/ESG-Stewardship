import React, { useState } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';

function App() {
    const [sessionId] = useState(`session_${Date.now()}`);

    return (
        <div className="App">
            <ChatInterface sessionId={sessionId} />
        </div>
    );
}

export default App;
