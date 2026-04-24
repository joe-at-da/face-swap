export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-screen bg-black">
      <div className="text-center space-y-4">
        <h1 className="text-2xl font-bold text-white">Clip Not Found</h1>
        <p className="text-sm text-gray-400">
          The clip you&apos;re trying to embed doesn&apos;t exist or has been removed.
        </p>
      </div>
    </div>
  );
}
