import React from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import ParliamentTVCapture from '../../components/parliament-tv/ParliamentTVCapture';

const ParliamentTVCapturePage: React.FC = () => {
  const router = useRouter();

  const handleSuccess = (data: any) => {
    console.log('Capture started successfully:', data);
  };

  const handleError = (error: any) => {
    console.error('Error starting capture:', error);
  };

  return (
    <>
      <Head>
        <title>Parliament TV Capture | The MP</title>
        <meta name="description" content="Capture Parliament TV streams with facial recognition" />
      </Head>

      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Parliament TV Capture</h1>
          <button
            onClick={() => router.push('/captures')}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            View All Captures
          </button>
        </div>

        <div className="mb-8">
          <p className="text-gray-600">
            Capture Parliament TV streams with facial recognition to automatically stop when the speaker is no longer present.
          </p>
        </div>

        <ParliamentTVCapture onSuccess={handleSuccess} onError={handleError} />

        <div className="mt-12 bg-gray-50 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">How to use Parliament TV Capture</h2>
          <ol className="list-decimal pl-5 space-y-2">
            <li>Enter a Parliament TV URL (e.g., https://parliamentlive.tv/event/index/12345678-1234-1234-1234-123456789012)</li>
            <li>Click "Validate" to check if the URL is valid and can be captured</li>
            <li>Enter a title and optional description for the capture</li>
            <li>Set the maximum duration (in seconds) for the capture</li>
            <li>Enable or disable facial recognition to automatically stop when the speaker is no longer present</li>
            <li>Click "Start Capture" to begin capturing the stream</li>
          </ol>
          <div className="mt-4 p-4 bg-yellow-50 rounded-md">
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> The capture will run in the background. You can view the status of your capture on the Captures page.
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

export default ParliamentTVCapturePage;
