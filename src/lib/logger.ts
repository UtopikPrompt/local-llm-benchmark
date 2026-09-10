// Logger for the browser-only benchmark tool. Logs to the browser console
// only; nothing is printed to the host's terminal.
export function logger(message: string): void {
  console.log(`[local-llm-benchmark] ${message}`);
}
