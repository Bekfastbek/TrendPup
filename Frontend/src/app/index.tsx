import Chat from '../components/Chat';

export default function Home() {
  return (
    <main className="min-h-screen p-4">
      <h1 className="text-2xl font-bold text-center mb-4">
        Injective Chain Chat
      </h1>
      <Chat />
    </main>
  );
}