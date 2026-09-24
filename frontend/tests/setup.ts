import '@testing-library/jest-dom';

class MockWebSocket extends EventTarget {
  url: string;
  readyState = 1;
  onopen: any = null;
  onclose: any = null;
  onmessage: any = null;
  onerror: any = null;

  constructor(url: string) {
    super();
    this.url = url;
    setTimeout(() => {
      this.onopen?.(new Event('open'));
      this.dispatchEvent(new Event('open'));
    }, 0);
  }

  send() {}
  close() {
    this.readyState = 3;
    setTimeout(() => {
      this.onclose?.(new Event('close'));
      this.dispatchEvent(new Event('close'));
    }, 0);
  }
}

globalThis.WebSocket = MockWebSocket as any;

// Minimal setup
export const server = {
  resetHandlers: () => {},
  close: () => {},
};
