'use client';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Global error page for handling root-level errors
 * This is a fallback for when the root layout or error.tsx fails
 * Uses inline styles only — no hooks, no imports — to stay prerenderable.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  return (
    <html>
      <head>
        <style>{`
          :root {
            --background: 0 0% 100%;
            --foreground: 240 10% 3.9%;
            --card: 0 0% 100%;
            --card-foreground: 240 10% 3.9%;
            --primary: 258 90% 66%;
            --primary-foreground: 210 40% 98%;
            --secondary: 240 4.8% 95.9%;
            --secondary-foreground: 240 5.9% 10%;
            --muted-foreground: 240 3.8% 46.1%;
            --destructive: 0 84.2% 60.2%;
            --destructive-foreground: 210 40% 98%;
            --border: 240 5.9% 90%;
            --radius: 0.75rem;
          }

          @media (prefers-color-scheme: dark) {
            :root {
              --background: 240 10% 3.9%;
              --foreground: 210 40% 98%;
              --card: 240 10% 3.9%;
              --card-foreground: 210 40% 98%;
              --primary: 258 90% 66%;
              --primary-foreground: 210 40% 98%;
              --secondary: 240 3.7% 15.9%;
              --secondary-foreground: 210 40% 98%;
              --muted-foreground: 240 5% 64.9%;
              --destructive: 0 62.8% 30.6%;
              --destructive-foreground: 210 40% 98%;
              --border: 240 3.7% 15.9%;
            }
          }

          * {
            border-color: hsl(var(--border));
          }

          body {
            background-color: hsl(var(--background));
            color: hsl(var(--foreground));
            font-family: "Roboto", system-ui, sans-serif;
            font-weight: 400;
            line-height: 1.5;
            margin: 0;
            padding: 0;
          }

          .ge-container {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
          }

          .ge-card {
            max-width: 32rem;
            width: 100%;
            background-color: hsl(var(--card));
            color: hsl(var(--card-foreground));
            border-radius: var(--radius);
            border: 1px solid hsl(var(--border));
            box-shadow: 0 1px 3px 0 hsl(var(--border) / 0.1);
            padding: 2rem;
          }

          .ge-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
          }

          .ge-error-icon {
            color: hsl(var(--destructive));
            width: 24px;
            height: 24px;
          }

          .ge-title {
            font-family: "Playfair Display", serif;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
            color: hsl(var(--destructive));
          }

          .ge-alert {
            background-color: hsl(var(--destructive) / 0.1);
            border: 1px solid hsl(var(--destructive) / 0.2);
            border-radius: calc(var(--radius) - 2px);
            padding: 1rem;
            margin-bottom: 1.5rem;
          }

          .ge-alert-title {
            font-size: 1rem;
            font-weight: 600;
            color: hsl(var(--destructive));
            margin: 0 0 0.5rem 0;
          }

          .ge-alert-description {
            font-size: 0.875rem;
            color: hsl(var(--destructive-foreground) / 0.8);
            margin: 0;
            line-height: 1.5;
          }

          .ge-error-info {
            font-size: 0.875rem;
            color: hsl(var(--muted-foreground));
            margin-bottom: 1.5rem;
          }

          .ge-error-info p {
            margin: 0 0 0.25rem 0;
          }

          .ge-error-code {
            font-size: 0.75rem;
            background-color: hsl(var(--secondary));
            color: hsl(var(--muted-foreground));
            padding: 0.25rem 0.5rem;
            border-radius: calc(var(--radius) - 4px);
            font-family: monospace;
          }

          .ge-button-group {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
          }

          .ge-button {
            flex: 1;
            min-width: 120px;
            padding: 0.75rem 1rem;
            border-radius: calc(var(--radius) - 2px);
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            border: none;
            transition: all 0.2s;
            font-family: inherit;
          }

          .ge-button-secondary {
            background-color: hsl(var(--secondary));
            color: hsl(var(--secondary-foreground));
            border: 1px solid hsl(var(--border));
          }

          .ge-button-secondary:hover {
            background-color: hsl(var(--secondary) / 0.8);
          }

          .ge-button-primary {
            background-color: hsl(var(--primary));
            color: hsl(var(--primary-foreground));
          }

          .ge-button-primary:hover {
            background-color: hsl(var(--primary) / 0.9);
          }

          .ge-footer {
            text-align: center;
            margin-top: 1.5rem;
            font-size: 0.875rem;
            color: hsl(var(--muted-foreground));
          }

          .ge-footer p {
            margin: 0;
          }

          @media (max-width: 640px) {
            .ge-container {
              padding: 1rem;
            }

            .ge-card {
              padding: 1.5rem;
            }

            .ge-button-group {
              flex-direction: column;
            }

            .ge-button {
              flex: none;
              width: 100%;
            }
          }
        `}</style>
      </head>
      <body>
        <div className="ge-container">
          <div className="ge-card">
            <div className="ge-header">
              <svg className="ge-error-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <h1 className="ge-title">Application Error</h1>
            </div>

            <div className="ge-alert">
              <h2 className="ge-alert-title">Critical Error</h2>
              <p className="ge-alert-description">
                A critical error has occurred in the application. This error has been automatically reported to our team.
              </p>
            </div>

            {error.digest && (
              <div className="ge-error-info">
                <p>
                  Error ID: <code className="ge-error-code">{error.digest}</code>
                </p>
                <p>This error has been automatically reported.</p>
              </div>
            )}

            <div className="ge-button-group">
              <button
                onClick={() => reset()}
                className="ge-button ge-button-secondary"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="ge-button ge-button-primary"
              >
                Reload Page
              </button>
            </div>

            <div className="ge-footer">
              <p>If this problem persists, please contact support.</p>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
