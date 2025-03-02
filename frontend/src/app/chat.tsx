   // pages/chat.tsx
   import { useState } from 'react';

   const Chat = () => {
     const [messages, setMessages] = useState<{ user: string; agent: string }[]>([]);
     const [input, setInput] = useState('');

     const sendMessage = async () => {
       const response = await fetch('/api/chat', {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
         },
         body: JSON.stringify({ message: input }),
       });
       const data = await response.json();
       setMessages((prev) => [...prev, { user: input, agent: data.response }]);
       setInput('');
     };

     return (
       <div className="flex flex-col items-center p-4">
         <h1 className="text-2xl font-bold mb-4">Chat with Agent</h1>
         <div className="w-full max-w-md border border-gray-300 rounded-lg p-4 mb-4">
           {messages.map((msg, index) => (
             <div key={index} className="mb-2">
               <strong>You:</strong> {msg.user}
               <br />
               <strong>Agent:</strong> {msg.agent}
             </div>
           ))}
         </div>
         <input
           type="text"
           value={input}
           onChange={(e) => setInput(e.target.value)}
           placeholder="Type your message..."
           className="border border-gray-300 rounded-lg p-2 w-full max-w-md"
         />
         <button
           onClick={sendMessage}
           className="bg-blue-500 text-white rounded-lg p-2 mt-2"
         >
           Send
         </button>
       </div>
     );
   };

   export default Chat;